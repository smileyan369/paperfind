import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session, get_db
from app.models.paper import Paper
from app.models.summary import Summary
from app.rate_limit import limiter
from app.schemas.summary import (
    BatchSummaryRequest,
    BatchSummaryResponse,
    SummaryResponse,
    SummaryStatsResponse,
)
from app.routers.config import get_effective_config
from app.services.summarizer import Summarizer
from app.services.summary_queue import get_summary_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/summary", tags=["summary"])


async def _check_ai_available():
    cfg = await get_effective_config()
    if not cfg["llm_api_key"]:
        raise HTTPException(status_code=503, detail="AI 摘要功能未启用：未配置 LLM API Key。请在 .env 文件或设置页面中填写 API Key。")


@router.post("/batch", response_model=BatchSummaryResponse)
async def summarize_batch(data: BatchSummaryRequest | None = None):
    """Manually trigger a batch summary run."""
    await _check_ai_available()
    limit = data.limit if data else 10
    queue = get_summary_queue()
    result = await queue.process_batch(batch_size=limit)
    return BatchSummaryResponse(
        success=result["success"],
        failed=result["failed"],
        errors=result["errors"],
    )


@router.post("/re-summarize", response_model=BatchSummaryResponse)
async def re_summarize_old_models(data: BatchSummaryRequest | None = None):
    """Re-summarize papers whose summaries were generated with a different model."""
    limit = data.limit if data else 10
    summarizer = Summarizer()
    result = await summarizer.re_summarize_old_models(limit=limit)
    return BatchSummaryResponse(
        success=result["success"],
        failed=result["failed"],
        errors=result["errors"],
    )


@router.post("/{paper_id}", response_model=SummaryResponse)
@limiter.limit("10/minute")
async def summarize_single(request: Request, paper_id: int):
    """User-requested summary — processed immediately with priority.

    If the paper is already being processed by the background queue,
    wait for it to complete (up to 60s), then return the result.
    """
    await _check_ai_available()
    async with async_session() as db:
        paper = await db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")

        result = await db.execute(select(Summary).where(Summary.paper_id == paper_id))
        existing = result.scalar_one_or_none()
        if existing and existing.status == "completed":
            return SummaryResponse.model_validate(existing)

    await Summarizer._pause_background()
    try:
        summarizer = Summarizer()
        summary = await summarizer.summarize_paper(paper_id)
        return SummaryResponse.model_validate(summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"摘要生成失败: {e}") from e
    finally:
        await Summarizer._resume_background()


@router.get("/stats", response_model=SummaryStatsResponse)
async def summary_stats(db: AsyncSession = Depends(get_db)):
    total_result = await db.execute(select(func.count(Summary.id)))
    total = total_result.scalar() or 0

    pending_result = await db.execute(
        select(func.count(Paper.id)).where(
            Paper.abstract.isnot(None),
            Paper.id.notin_(select(Summary.paper_id).where(Summary.status.in_(["completed", "processing"]))),
        )
    )
    pending = pending_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(Summary.id)).where(Summary.status == "failed")
    )
    failed = failed_result.scalar() or 0

    return SummaryStatsResponse(
        total_summaries=total,
        pending_count=pending,
        failed_count=failed,
    )


@router.get("/queue")
async def get_queue_status():
    """Get the current state of the summary queue."""
    q = get_summary_queue()
    return q.stats


@router.get("/progress")
async def get_summary_progress():
    """Get detailed summary progress: totals, remaining, currently processing."""
    q = get_summary_queue()
    return await q.detailed_stats()


@router.get("/{paper_id}/stream")
async def stream_summary(paper_id: int, request: Request):
    """Stream AI summary generation via SSE. Real-time text output."""
    await _check_ai_available()
    from fastapi.responses import StreamingResponse
    import json

    async with async_session() as db:
        paper = await db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")

    summarizer = Summarizer()

    async def event_stream():
        try:
            async for chunk in summarizer.stream_summarize(paper_id):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
