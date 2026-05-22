# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 论文搜搜 single-exe distribution.

Build command:
    pyinstaller paperfind.spec

Output: dist/论文搜搜.exe
"""

from pathlib import Path

_block_cipher = None

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent
BACKEND = SPEC_DIR
FRONTEND_DIST = ROOT / "frontend" / "dist"

added_files = []

if FRONTEND_DIST.exists():
    added_files.append((str(FRONTEND_DIST), "frontend/dist"))

jcr_csv = BACKEND / "data" / "jcr_seed.csv"
if jcr_csv.exists():
    added_files.append((str(jcr_csv), "data"))

a = Analysis(
    ['run.py'],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        # Application modules
        "app",
        "app.config",
        "app.database",
        "app.main",
        "app.rate_limit",
        "app.models",
        "app.models.__init__",
        "app.models.app_config",
        "app.models.crawl_log",
        "app.models.journal",
        "app.models.keyword",
        "app.models.paper",
        "app.models.summary",
        "app.routers",
        "app.routers.__init__",
        "app.routers.config",
        "app.routers.crawl",
        "app.routers.journals",
        "app.routers.keywords",
        "app.routers.papers",
        "app.routers.summary",
        "app.services",
        "app.services.crawler",
        "app.services.crawler.__init__",
        "app.services.crawler.orchestrator",
        "app.services.sci_lookup",
        "app.services.scheduler_service",
        "app.services.summarizer",
        "app.services.summary_queue",
        # Dependencies
        "openai",
        "httpx",
        "apscheduler",
        "apscheduler.schedulers.asyncio",
        "pydantic_settings",
        "slowapi",
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
        "aiosqlite",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "starlette.middleware",
        "starlette.middleware.base",
        "starlette.middleware.cors",
        "fastapi",
        "fastapi.staticfiles",
        "fastapi.responses",
        # pywebview + dependencies
        "webview",
        "webview.http",
        "webview.platforms",
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
        "webview.platforms.cef",
        "webview.js",
        "webview.util",
        "bottle",
        "clr_loader",
        "pythonnet",
        "proxy_tools",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=_block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=_block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="论文搜搜",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)
