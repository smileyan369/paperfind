import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.config import load_llm_config_backup, save_llm_config_backup, settings
from app.database import async_session
from app.models.app_config import AppConfig
from app.models.keyword import Keyword

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigResponse(BaseModel):
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    auto_summary_enabled: bool
    research_profile: str
    ai_available: bool


class ConfigUpdateRequest(BaseModel):
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    auto_summary_enabled: bool | None = None
    research_profile: str | None = None


class HistoryEntry(BaseModel):
    text: str
    added_at: str


class KeywordHistoryUpdate(BaseModel):
    entries: list[HistoryEntry]


async def _load_config() -> dict[str, str]:
    config: dict[str, str] = {}
    async with async_session() as db:
        result = await db.execute(select(AppConfig))
        for row in result.scalars().all():
            config[row.key] = row.value
    return config


async def _save_config(updates: dict[str, str]):
    async with async_session() as db:
        for key, value in updates.items():
            stmt = select(AppConfig).where(AppConfig.key == key)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.value = value
            else:
                db.add(AppConfig(key=key, value=value))
        await db.commit()


async def _save_config_value(key: str, value: str):
    await _save_config({key: value})


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]


def _is_masked_key(key: str) -> bool:
    return key.startswith("****")


def _to_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


async def get_effective_config() -> dict[str, str | bool]:
    db_cfg = await _load_config()
    backup_cfg = load_llm_config_backup()
    llm_api_key = db_cfg.get("llm_api_key") or backup_cfg.get("llm_api_key") or settings.llm_api_key
    llm_base_url = db_cfg.get("llm_base_url") or backup_cfg.get("llm_base_url") or settings.llm_base_url
    llm_model = db_cfg.get("llm_model") or backup_cfg.get("llm_model") or settings.llm_model

    restore_updates = {
        key: value
        for key, value in {
            "llm_api_key": llm_api_key,
            "llm_base_url": llm_base_url,
            "llm_model": llm_model,
        }.items()
        if value and not db_cfg.get(key)
    }
    if restore_updates:
        await _save_config(restore_updates)

    return {
        "llm_api_key": llm_api_key,
        "llm_base_url": llm_base_url,
        "llm_model": llm_model,
        "auto_summary_enabled": _to_bool(db_cfg.get("auto_summary_enabled")),
        "research_profile": db_cfg.get("research_profile", ""),
    }


async def sync_summary_queue_from_config(cfg: dict[str, str | bool] | None = None):
    if cfg is None:
        cfg = await get_effective_config()

    from app.services.summary_queue import get_summary_queue

    queue = get_summary_queue()
    should_run = bool(cfg["llm_api_key"]) and bool(cfg["auto_summary_enabled"])
    if should_run:
        queue.start(batch_size=1, idle_seconds=60)
    else:
        await queue.stop()


@router.get("", response_model=ConfigResponse)
async def get_config():
    cfg = await get_effective_config()
    return ConfigResponse(
        llm_api_key=_mask_key(cfg["llm_api_key"]),
        llm_base_url=cfg["llm_base_url"],
        llm_model=cfg["llm_model"],
        auto_summary_enabled=bool(cfg["auto_summary_enabled"]),
        research_profile=str(cfg["research_profile"]),
        ai_available=bool(cfg["llm_api_key"]),
    )


@router.put("", response_model=ConfigResponse)
async def update_config(data: ConfigUpdateRequest):
    updates: dict[str, str] = {}
    if data.llm_api_key is not None and not _is_masked_key(data.llm_api_key):
        updates["llm_api_key"] = data.llm_api_key
    if data.llm_base_url is not None:
        updates["llm_base_url"] = data.llm_base_url
    if data.llm_model is not None:
        updates["llm_model"] = data.llm_model
    if data.auto_summary_enabled is not None:
        updates["auto_summary_enabled"] = "true" if data.auto_summary_enabled else "false"
    if data.research_profile is not None:
        updates["research_profile"] = data.research_profile.strip()

    if updates:
        await _save_config(updates)
        save_llm_config_backup({
            key: value
            for key, value in updates.items()
            if key in {"llm_api_key", "llm_base_url", "llm_model"}
        })
        # Sync to in-memory settings so AI services pick up the new config immediately
        if "llm_api_key" in updates:
            settings.llm_api_key = updates["llm_api_key"]
        if "llm_base_url" in updates:
            settings.llm_base_url = updates["llm_base_url"]
        if "llm_model" in updates:
            settings.llm_model = updates["llm_model"]

    cfg = await get_effective_config()
    await sync_summary_queue_from_config(cfg)
    return ConfigResponse(
        llm_api_key=_mask_key(cfg["llm_api_key"]),
        llm_base_url=cfg["llm_base_url"],
        llm_model=cfg["llm_model"],
        auto_summary_enabled=bool(cfg["auto_summary_enabled"]),
        research_profile=str(cfg["research_profile"]),
        ai_available=bool(cfg["llm_api_key"]),
    )


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/keyword-history")
async def get_keyword_history():
    cfg = await _load_config()
    raw = cfg.get("keyword_history", "[]")
    try:
        entries = json.loads(raw)
        if not isinstance(entries, list):
            entries = []
    except json.JSONDecodeError:
        entries = []
    if not entries:
        async with async_session() as db:
            result = await db.execute(
                select(Keyword).order_by(Keyword.created_at.desc()).limit(30)
            )
            entries = [
                {
                    "text": kw.text,
                    "added_at": kw.created_at.isoformat() if kw.created_at else "",
                }
                for kw in result.scalars().all()
            ]
    return {"entries": entries[:30]}


@router.put("/keyword-history")
async def update_keyword_history(data: KeywordHistoryUpdate):
    entries = [
        {"text": item.text.strip(), "added_at": item.added_at}
        for item in data.entries
        if item.text.strip()
    ][:30]
    await _save_config_value("keyword_history", json.dumps(entries, ensure_ascii=False))
    return {"entries": entries}
