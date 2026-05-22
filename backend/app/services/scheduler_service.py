import logging
from datetime import datetime, timezone

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None

JOB_ID_DAILY_CRAWL = "daily_crawl"
JOB_ID_DAILY_SUMMARY = "daily_summary"


def init_scheduler() -> AsyncIOScheduler:
    global scheduler

    jobstores = {
        "default": SQLAlchemyJobStore(url=settings.database_url.replace("+aiosqlite", ""))
    }

    scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="Asia/Shanghai")

    # Daily crawl job
    scheduler.add_job(
        _run_daily_crawl,
        "cron",
        hour=settings.crawl_schedule_hour,
        minute=settings.crawl_schedule_minute,
        id=JOB_ID_DAILY_CRAWL,
        replace_existing=True,
    )

    # Daily summary job (2 hours after crawl)
    summary_hour = (settings.crawl_schedule_hour + 2) % 24
    scheduler.add_job(
        _run_daily_summary,
        "cron",
        hour=summary_hour,
        minute=settings.crawl_schedule_minute,
        id=JOB_ID_DAILY_SUMMARY,
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started: daily crawl at %02d:%02d, summary at %02d:%02d",
        settings.crawl_schedule_hour,
        settings.crawl_schedule_minute,
        summary_hour,
        settings.crawl_schedule_minute,
    )
    return scheduler


async def _run_daily_crawl():
    from app.services.crawler.orchestrator import CrawlOrchestrator

    logger.info("Scheduled daily crawl starting...")
    orch = CrawlOrchestrator()
    await orch.run_full_crawl(source="all", trigger="scheduled")
    logger.info("Scheduled daily crawl completed")


async def _run_daily_summary():
    from app.routers.config import get_effective_config
    from app.services.summary_queue import get_summary_queue

    cfg = await get_effective_config()
    if not cfg["llm_api_key"] or not cfg["auto_summary_enabled"]:
        logger.info("Scheduled daily summary skipped: auto summary disabled or AI unavailable")
        return

    logger.info("Scheduled daily summary starting...")
    q = get_summary_queue()
    # Process a larger batch for the scheduled run
    await q.process_batch(batch_size=10)
    logger.info("Scheduled daily summary batch completed")


def get_scheduler_status() -> dict:
    if scheduler is None:
        return {"next_run": None, "last_run": None, "job_id": None, "running": False}

    daily_job = scheduler.get_job(JOB_ID_DAILY_CRAWL)
    return {
        "running": scheduler.running,
        "daily_crawl": {
            "next_run": daily_job.next_run_time.isoformat() if daily_job and daily_job.next_run_time else None,
        },
    }


def shutdown_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
