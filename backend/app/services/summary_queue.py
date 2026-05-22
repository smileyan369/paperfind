"""
AI Summary background queue with priority support.

- User-requested summaries (via POST /api/summary/{id}) get immediate priority
- Background worker processes ALL remaining papers continuously when user is idle
- Processing order: keyword-matched papers first → SCI zone (Q1→Q4) → date (newest)
- Only counts papers with actual summary content as "done"
"""

import asyncio
import logging
from collections import deque

from sqlalchemy import case, exists, func, select

from app.config import settings
from app.database import async_session
from app.models.keyword import Keyword
from app.models.paper import Paper, paper_keywords
from app.models.summary import Summary
from app.services.summarizer import Summarizer

logger = logging.getLogger(__name__)


class SummaryQueueManager:
    """Singleton that manages the summary processing queue."""

    _instance: "SummaryQueueManager | None" = None

    def __init__(self):
        self._user_queue: deque[int] = deque()
        self._processing: set[int] = set()
        self._lock = asyncio.Lock()
        self._bg_task: asyncio.Task | None = None
        self._running = False

    @classmethod
    def get(cls) -> "SummaryQueueManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def enqueue_user_request(self, paper_id: int):
        """User explicitly requested summary. Goes to front of the line."""
        async with self._lock:
            if paper_id not in self._processing and paper_id not in self._user_queue:
                self._user_queue.appendleft(paper_id)
                logger.info("User requested summary for paper %d — queued with priority", paper_id)

    async def _get_next(self, limit: int) -> list[int]:
        """Get up to `limit` papers to summarize. User queue first, then DB order."""
        batch: list[int] = []

        # 1. Drain user priority queue first
        async with self._lock:
            while self._user_queue and len(batch) < limit:
                pid = self._user_queue.popleft()
                if pid not in self._processing:
                    batch.append(pid)
                    self._processing.add(pid)

        # 2. Fill remaining slots from DB.
        #    Priority: keyword-matched papers first → Q1→Q2→Q3→Q4 → newest date
        #    Only process papers linked to at least one ACTIVE keyword
        remaining = limit - len(batch)
        if remaining > 0:
            async with async_session() as db:
                zone_order = case(
                    (Paper.sci_zone == "Q1", 0),
                    (Paper.sci_zone == "Q2", 1),
                    (Paper.sci_zone == "Q3", 2),
                    (Paper.sci_zone == "Q4", 3),
                    else_=4,
                )

                # Papers linked to any ACTIVE keyword get priority 0, rest get 1
                # Ensure keyword and paper belong to same user
                has_active_keywords = exists().where(
                    paper_keywords.c.paper_id == Paper.id,
                    paper_keywords.c.keyword_id == Keyword.id,
                    Keyword.is_active == True,
                )
                keyword_priority = case((has_active_keywords, 0), else_=1)

                # Get papers that need summarizing:
                # - No summary at all, OR
                # - Summary exists but failed/truncated, OR
                # - Summary completed but with old/different model
                # Exclude: papers with CURRENT-model completed summary, or currently processing
                excluded = (
                    select(Summary.paper_id).where(
                        Summary.status.in_(["processing"]),
                    )
                ).union(
                    select(Summary.paper_id).where(
                        Summary.status == "completed",
                        Summary.model_used == settings.llm_model,
                    )
                )
                result = await db.execute(
                    select(Paper.id)
                    .where(
                        Paper.id.in_(
                            select(paper_keywords.c.paper_id).where(
                                paper_keywords.c.keyword_id == Keyword.id,
                                Keyword.is_active == True,
                            ).distinct()
                        ),
                        Paper.id.notin_(excluded),
                        Paper.id.notin_(list(self._processing) + batch),
                    )
                    .order_by(keyword_priority, zone_order, Paper.publication_date.desc())
                    .limit(remaining)
                )
                db_ids = [r[0] for r in result.all()]

            async with self._lock:
                for pid in db_ids:
                    if pid not in batch and pid not in self._processing:
                        batch.append(pid)
                        self._processing.add(pid)

        return batch

    async def _mark_done(self, paper_ids: list[int]):
        async with self._lock:
            for pid in paper_ids:
                self._processing.discard(pid)

    async def _process_one(self, paper_id: int, summarizer: Summarizer) -> bool:
        try:
            await summarizer.summarize_paper(paper_id)
            logger.info("Summary generated for paper %d", paper_id)
            return True
        except Exception as e:
            logger.error("Summary failed for paper %d: %s", paper_id, e)
            return False

    async def process_batch(self, batch_size: int = 10) -> dict:
        """Process one batch of summaries sequentially (avoids SQLite greenlet conflicts)."""
        batch = await self._get_next(batch_size)
        if not batch:
            return {"success": 0, "failed": 0, "errors": []}

        logger.info("Processing summary batch (%d papers): %s...", len(batch), batch[:3])
        summarizer = Summarizer()
        success = 0
        failed = 0
        errors: list[dict] = []

        for pid in batch:
            try:
                ok = await self._process_one(pid, summarizer)
                if ok:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                errors.append({"paper_id": pid, "error": str(e)})

        await self._mark_done(batch)
        # Clean up per-paper locks to avoid unbounded growth
        for pid in batch:
            Summarizer._locks.pop(pid, None)
        logger.info("Batch complete: %d/%d success", success, len(batch))
        return {"success": success, "failed": failed, "errors": errors}

    async def _count_remaining(self) -> int:
        """Count papers that still need summaries (only those linked to active keywords)."""
        async with async_session() as db:
            excluded = (
                select(Summary.paper_id).where(Summary.status == "processing")
            ).union(
                select(Summary.paper_id).where(
                    Summary.status == "completed",
                    Summary.model_used == settings.llm_model,
                )
            )
            result = await db.execute(
                select(func.count(Paper.id))
                .where(
                    Paper.abstract.isnot(None),
                    Paper.id.notin_(excluded),
                    Paper.id.in_(
                        select(paper_keywords.c.paper_id).where(
                            paper_keywords.c.keyword_id == Keyword.id,
                            Keyword.is_active == True,
                        ).distinct()
                    ),
                )
            )
            return result.scalar() or 0

    async def run_background(self, batch_size: int = 10, idle_seconds: int = 60):
        """Continuous background loop: process ALL pending papers, then idle."""
        self._running = True
        logger.info("Summary background worker started (batch=%d, idle=%ds)", batch_size, idle_seconds)

        while self._running:
            try:
                # Process continuously until no more papers need summarizing
                while self._running:
                    # Pause while user is streaming a summary (user gets priority)
                    if Summarizer._user_streaming_count > 0:
                        await Summarizer._user_streaming_changed.wait()
                        continue
                    remaining = await self._count_remaining()
                    if remaining == 0:
                        break
                    logger.info("Background summary: %d papers remaining", remaining)
                    await self.process_batch(batch_size)
                    # Small delay between batches to avoid hammering the API
                    await asyncio.sleep(1)
            except Exception as e:
                logger.exception("Background summary error: %s", e)

            # All done — wait before checking for new papers
            if self._running:
                logger.info("Summary queue empty, idling %ds", idle_seconds)
                await asyncio.sleep(idle_seconds)

    def start(self, batch_size: int = 10, idle_seconds: int = 60):
        """Start the background worker as an asyncio task."""
        if self._bg_task and not self._bg_task.done():
            return
        self._bg_task = asyncio.create_task(self.run_background(batch_size, idle_seconds))

    async def stop(self):
        """Stop the background worker."""
        self._running = False
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()
            try:
                await self._bg_task
            except asyncio.CancelledError:
                pass
        logger.info("Summary background worker stopped")

    @property
    def stats(self) -> dict:
        return {
            "user_queue_size": len(self._user_queue),
            "currently_processing": len(self._processing),
            "running": self._running,
        }

    async def detailed_stats(self) -> dict:
        """Return detailed stats including what's being processed and total counts."""
        async with async_session() as db:
            # Currently processing paper IDs
            async with self._lock:
                processing_ids = list(self._processing)

            # Fetch titles of papers currently being summarized
            processing_titles = []
            if processing_ids:
                result = await db.execute(
                    select(Paper.id, Paper.title).where(Paper.id.in_(processing_ids))
                )
                processing_titles = [{"id": r[0], "title": r[1]} for r in result.all()]

            # Subquery: papers linked to at least one active keyword
            active_kw_papers = select(paper_keywords.c.paper_id).where(
                paper_keywords.c.keyword_id == Keyword.id,
                Keyword.is_active == True,
            ).distinct()

            # Total summarized for display: any completed summary counts, regardless of model.
            total_any_result = await db.execute(
                select(func.count(Summary.id)).where(
                    Summary.status == "completed",
                    Summary.paper_id.in_(active_kw_papers),
                )
            )
            total_summarized_any_model = total_any_result.scalar() or 0

            current_model_result = await db.execute(
                select(func.count(Summary.id)).where(
                    Summary.status == "completed",
                    Summary.model_used == settings.llm_model,
                    Summary.paper_id.in_(active_kw_papers),
                )
            )
            total_summarized_current_model = current_model_result.scalar() or 0

            outdated_result = await db.execute(
                select(func.count(Summary.id)).where(
                    Summary.status == "completed",
                    Summary.model_used != settings.llm_model,
                    Summary.paper_id.in_(active_kw_papers),
                )
            )
            outdated_summary_count = outdated_result.scalar() or 0

            # Total papers that will eventually need summary (only active-keyword papers)
            total_papers_result = await db.execute(
                select(func.count(Paper.id)).where(
                    Paper.id.in_(active_kw_papers)
                )
            )
            total_papers = total_papers_result.scalar() or 0

            # Remaining (needs summarizing or re-summarizing), same logic as _count_remaining
            excluded = (
                select(Summary.paper_id).where(Summary.status == "processing")
            ).union(
                select(Summary.paper_id).where(
                    Summary.status == "completed",
                    Summary.model_used == settings.llm_model,
                )
            )
            remaining_result = await db.execute(
                select(func.count(Paper.id))
                .where(
                    Paper.abstract.isnot(None),
                    Paper.id.notin_(excluded),
                    Paper.id.in_(active_kw_papers),
                )
            )
            remaining_with_abstract = remaining_result.scalar() or 0

            # Also count papers without abstracts that need re-summarizing
            no_abstract_result = await db.execute(
                select(func.count(Paper.id))
                .where(
                    Paper.abstract.is_(None),
                    Paper.id.in_(active_kw_papers),
                    Paper.id.in_(
                        select(Summary.paper_id).where(
                            Summary.status == "completed",
                            Summary.model_used != settings.llm_model,
                        )
                    ),
                )
            )
            remaining_no_abstract = no_abstract_result.scalar() or 0

            return {
                "total_papers": total_papers,
                "total_summarized": total_summarized_any_model,
                "total_summarized_any_model": total_summarized_any_model,
                "total_summarized_current_model": total_summarized_current_model,
                "outdated_summary_count": outdated_summary_count,
                "remaining": remaining_with_abstract + remaining_no_abstract,
                "currently_processing": processing_titles,
                "running": self._running,
            }


def get_summary_queue() -> SummaryQueueManager:
    return SummaryQueueManager.get()
