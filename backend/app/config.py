import os
import json
import shutil
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_dev_root = Path(__file__).resolve().parent.parent.parent
_exe_root = Path(sys.executable).parent if getattr(sys, "frozen", False) else _dev_root


def _windows_roaming_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "PaperFind"
    return Path.home() / "AppData" / "Roaming" / "PaperFind"


def _resolve_data_dir() -> Path:
    """Use a stable user data folder for packaged exe updates.

    Older builds stored data beside the exe.  On first run after this change,
    copy that database into the stable folder so API keys, keywords, papers and
    logs survive updates and moving the exe.
    """
    if getattr(sys, "frozen", False):
        stable = _windows_roaming_dir()
        stable.mkdir(parents=True, exist_ok=True)
        old_data = _exe_root / "data"
        for name in ("papers.db", "papers.db-shm", "papers.db-wal"):
            src = old_data / name
            dst = stable / name
            if src.exists() and not dst.exists():
                try:
                    shutil.copy2(src, dst)
                except OSError:
                    pass
        return stable
    return _dev_root / "data"


_app_root = _exe_root
_data_dir = _resolve_data_dir()
_data_dir.mkdir(parents=True, exist_ok=True)
_llm_config_backup_path = _data_dir / "llm_config_backup.json"


def load_llm_config_backup() -> dict[str, str]:
    if not _llm_config_backup_path.exists():
        return {}
    try:
        raw = json.loads(_llm_config_backup_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        "llm_api_key": str(raw.get("llm_api_key") or ""),
        "llm_base_url": str(raw.get("llm_base_url") or ""),
        "llm_model": str(raw.get("llm_model") or ""),
    }


def save_llm_config_backup(values: dict[str, str]) -> None:
    current = load_llm_config_backup()
    current.update({key: value for key, value in values.items() if key in current or key.startswith("llm_")})
    try:
        _llm_config_backup_path.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass

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
