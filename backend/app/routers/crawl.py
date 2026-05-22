import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.database import get_db
from app.models.crawl_log import CrawlLog
from app.rate_limit import limiter
from app.schemas.crawl import (
    CrawlLogListResponse,
    CrawlLogResponse,
    CrawlTriggerRequest,
    CrawlTriggerResponse,
    UnreachableSource,
)
from app.services.crawler.orchestrator import CrawlOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crawl", tags=["crawl"])
orchestrator = CrawlOrchestrator()


# ── Global crawl event bus ──────────────────────────────────────────────

class CrawlEventBus:
    """Decouples crawl execution from SSE connections. Crawl keeps running
    even when all subscribers disconnect (e.g. page refresh)."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue[dict | None]] = []
        self._task: asyncio.Task | None = None
        self.running = False
        self.source = "all"
        self.papers_new = 0
        self.papers_found = 0
        self.new_papers: list[dict] = []
        self.unreachable_sources: list[dict] = []
        self.message = ""

    def subscribe(self) -> asyncio.Queue[dict | None]:
        q: asyncio.Queue[dict | None] = asyncio.Queue()
        self._subscribers.append(q)
        # Replay current state to late subscriber
        if self.running:
            q.put_nowait({
                "type": "status",
                "running": True,
                "source": self.source,
                "papers_new": self.papers_new,
                "papers_found": self.papers_found,
                "message": self.message,
            })
            for paper in self.new_papers:
                q.put_nowait({"type": "paper_new", "paper": paper})
        return q

    def unsubscribe(self, q: asyncio.Queue):
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def _broadcast(self, event: dict):
        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)

    def start(self, source: str, keyword_ids: list[int] | None):
        if self.running:
            return
        self.running = True
        self.source = source
        self.papers_new = 0
        self.papers_found = 0
        self.new_papers = []
        self.unreachable_sources = []
        self.message = "正在检索..."
        self._task = asyncio.create_task(self._run(source, keyword_ids))

    async def _run(self, source: str, keyword_ids: list[int] | None):
        queue: asyncio.Queue[dict] = asyncio.Queue()
        try:
            log = await orchestrator.run_full_crawl(
                source=source, trigger="manual",
                keyword_ids=keyword_ids,
                event_queue=queue,
            )

            while True:
                try:
                    event = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                if event["type"] == "paper_new":
                    self.papers_new += 1
                    if event.get("paper"):
                        self.new_papers.append(event["paper"])
                    self.message = f"正在检索... (已找到 {self.papers_new} 篇)"
                elif event["type"] == "complete":
                    self.papers_found = event.get("papers_found", 0)
                    self.papers_new = event.get("papers_new", 0)
                    if self.papers_new > 0:
                        self.message = f"检索完成：新增 {self.papers_new} 篇"
                    else:
                        self.message = event.get("message", "检索完成，未发现新论文")
                    if event.get("unreachable_sources"):
                        self.unreachable_sources = event["unreachable_sources"]
                elif event["type"] == "error":
                    self.message = event.get("message", "检索失败")

                self._broadcast(event)

                if event["type"] in ("complete", "error"):
                    break
        except Exception as e:
            logger.exception("Background crawl failed")
            self._broadcast({"type": "error", "message": str(e)})
        finally:
            self.running = False
            self._task = None

    def get_status(self) -> dict:
        return {
            "running": self.running,
            "source": self.source,
            "papers_new": self.papers_new,
            "papers_found": self.papers_found,
            "message": self.message,
        }


crawl_bus = CrawlEventBus()


# ── Endpoints ───────────────────────────────────────────────────────────

@router.post("", response_model=CrawlTriggerResponse)
@limiter.limit("10/minute")
async def trigger_crawl(request: Request, data: CrawlTriggerRequest):
    source = data.source
    if source not in ("all", "arxiv", "semantic_scholar", "dblp", "google_scholar", "jnu_library", "ieee", "acm"):
        raise HTTPException(status_code=400, detail=f"Invalid source: {source}")

    log = await orchestrator.run_full_crawl(source=source, trigger="manual", keyword_ids=data.keyword_ids)
    return CrawlTriggerResponse(
        crawl_log_id=log.id,
        message=f"Crawl completed: {log.papers_new} new, {log.papers_updated} updated",
        unreachable_sources=[UnreachableSource(**u) for u in orchestrator.unreachable_sources],
    )


@router.post("/stream")
@limiter.limit("10/minute")
async def trigger_crawl_stream(request: Request, data: CrawlTriggerRequest):
    source = data.source
    if source not in ("all", "arxiv", "semantic_scholar", "dblp", "google_scholar", "jnu_library", "ieee", "acm"):
        raise HTTPException(status_code=400, detail=f"Invalid source: {source}")

    crawl_bus.start(source, data.keyword_ids)
    q = crawl_bus.subscribe()

    async def event_stream():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=300)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'timeout'})}\n\n"
                    break

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if event is None or event.get("type") in ("complete", "error"):
                    break
        finally:
            crawl_bus.unsubscribe(q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status")
async def crawl_status():
    return crawl_bus.get_status()


@router.get("/logs", response_model=CrawlLogListResponse)
async def list_crawl_logs(
    page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db)
):
    total_query = select(func.count(CrawlLog.id))
    total = (await db.execute(total_query)).scalar() or 0

    result = await db.execute(
        select(CrawlLog)
        .order_by(desc(CrawlLog.started_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    logs = result.scalars().all()

    return CrawlLogListResponse(
        logs=[CrawlLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/schedule")
async def get_schedule():
    from app.services.scheduler_service import get_scheduler_status
    return get_scheduler_status()


@router.put("/schedule")
async def update_schedule(hour: int = 8, minute: int = 0):
    from app.services.scheduler_service import scheduler

    if scheduler is None:
        return {"error": "Scheduler not initialized"}

    job = scheduler.get_job("daily_crawl")
    if job:
        job.reschedule("cron", hour=hour, minute=minute)
    return {"message": f"Schedule updated to {hour:02d}:{minute:02d}", "next_run": str(job.next_run_time) if job else None}
