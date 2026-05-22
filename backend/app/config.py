import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve data directory: next to .exe when frozen, otherwise project root
if getattr(sys, 'frozen', False):
    _app_root = Path(sys.executable).parent
else:
    _app_root = Path(__file__).resolve().parent.parent.parent

_data_dir = _app_root / "data"
_data_dir.mkdir(parents=True, exist_ok=True)

_env_path = Path(os.getcwd()) / ".env"
if not _env_path.exists():
    _env_path = _app_root / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_path) if _env_path.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = f"sqlite+aiosqlite:///{_data_dir / 'papers.db'}"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    crawl_schedule_hour: int = 8
    crawl_schedule_minute: int = 0
    crawl_rate_limit_rps: int = 3
    summary_batch_size: int = 5
    summary_max_retries: int = 3
    proxy_url: str = ""
    ieee_institution_cookie: str | None = None
    acm_institution_cookie: str | None = None
    frontend_origin: str = "http://localhost:5173"
    log_level: str = "INFO"


settings = Settings()
