import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import async_session, init_db

import app.models  # noqa: F401

from app.routers import keywords as keywords_router
from app.routers import crawl as crawl_router
from app.routers import journals as journals_router
from app.routers import papers as papers_router
from app.routers import summary as summary_router
from app.routers import config as config_router

from app.rate_limit import limiter

logger = logging.getLogger(__name__)


def _resource_path(relative: str) -> Path:
    """Return a Path for a bundled resource. Works in dev and PyInstaller frozen mode."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).resolve().parent.parent.parent / relative


FRONTEND_DIR = _resource_path("frontend/dist")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from app.services.sci_lookup import seed_journals_from_csv
    from app.services.scheduler_service import init_scheduler, shutdown_scheduler
    from app.services.summary_queue import get_summary_queue

    await seed_journals_from_csv(str(_resource_path("data/jcr_seed.csv")))
    init_scheduler()

    # Load LLM config from DB (user may have saved via settings page)
    from app.routers.config import get_effective_config, sync_summary_queue_from_config
    cfg = await get_effective_config()
    if cfg["llm_api_key"]:
        settings.llm_api_key = cfg["llm_api_key"]
    if cfg["llm_base_url"]:
        settings.llm_base_url = cfg["llm_base_url"]
    if cfg["llm_model"]:
        settings.llm_model = cfg["llm_model"]

    # Clean old Groq defaults that may be stored in DB from earlier versions
    from app.models.app_config import AppConfig
    from sqlalchemy import select, delete as sa_delete
    async with async_session() as db:
        old_defaults = {
            "llm_base_url": "https://api.groq.com/openai/v1",
            "llm_model": "llama-3.1-8b-instant",
        }
        for k, v in old_defaults.items():
            row = await db.execute(select(AppConfig).where(AppConfig.key == k, AppConfig.value == v))
            if row.scalar_one_or_none():
                await db.execute(sa_delete(AppConfig).where(AppConfig.key == k))
                logger.info("Cleaned old default '%s' from DB", k)
        await db.commit()

    from app.models.summary import Summary
    from sqlalchemy import update
    async with async_session() as db:
        result = await db.execute(
            update(Summary)
            .where(Summary.status == "processing")
            .values(status="failed", error_message="Server restart — reset")
        )
        if result.rowcount:
            logger.info("Reset %d stuck processing summaries", result.rowcount)
        await db.commit()

    summary_queue = get_summary_queue()
    await sync_summary_queue_from_config(cfg)

    yield

    await summary_queue.stop()
    shutdown_scheduler()


app = FastAPI(
    title="论文搜搜",
    description="从各大论文平台爬取论文，AI摘要，SCI分区标注",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(keywords_router.router)
app.include_router(crawl_router.router)
app.include_router(journals_router.router)
app.include_router(papers_router.router)
app.include_router(summary_router.router)
app.include_router(config_router.router)


@app.get("/")
async def root():
    index_html = FRONTEND_DIR / "index.html"
    if index_html.exists():
        return FileResponse(index_html)
    return {"message": "论文搜搜 API", "version": "0.1.0"}


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    file_path = FRONTEND_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    index_html = FRONTEND_DIR / "index.html"
    if index_html.exists():
        return FileResponse(index_html)
    return {"detail": "Not found"}, 404
