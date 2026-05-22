# 论文搜搜 (PaperFind) — 项目完整总结

> 写给接手此项目的高级程序员，帮助你快速了解项目全貌、架构设计、历史演变和关键决策。

---

## 一、软件是什么

**论文搜搜**是一个 Windows 桌面论文检索工具。用户输入关键词后，系统自动从多个学术平台（ArXiv、Semantic Scholar、DBLP、Google Scholar 等）并发爬取论文，经过去重、关键词相关性过滤后存入本地 SQLite 数据库。入库的论文可一键触发 AI 生成中文摘要（支持 OpenAI 兼容 API），并自动标注 SCI 分区。

**核心特点**：
- 打包为单个 `.exe` 文件（~224MB），双击即用，无需安装任何依赖
- 完全本地运行，数据存储在 `data/papers.db`，无需联网（仅爬取 + AI 摘要需要）
- 原生 Windows 窗口（非浏览器），无终端黑窗，有启动动画

---

## 二、技术架构全景

```
论文搜搜.exe (PyInstaller --onefile --noconsole, ~224MB)
│
├─【桌面壳】pywebview (Edge WebView2)
│   ├── Splash HTML: 启动动画（紫色 Logo + CSS 脉冲 + 圆点 loading）
│   ├── JS 轮询 http://127.0.0.1:8001 → 服务就绪后自动跳转
│   └── Win32 API WM_SETICON: 显式设置窗口标题栏图标
│
├─【前端】React 18 + TypeScript + Vite + Tailwind CSS
│   ├── vite-plugin-singlefile: 所有 JS/CSS 内联到单个 index.html (~363KB gzip: ~112KB)
│   ├── HashRouter: 3 个路由 (/, /keywords, /settings)
│   ├── SSE EventSource: 实时接收爬取进度 + 新论文通知
│   └── localStorage: AI 配置 + 搜索历史 + 欢迎弹窗状态
│
├─【后端】Python FastAPI + uvicorn (127.0.0.1:8001)
│   ├── ORM: SQLAlchemy 2.x async + aiosqlite
│   ├── 爬虫层: 7 个爬虫适配器，asyncio.gather 并发
│   ├── AI 摘要层: OpenAI-compatible API (Groq / 自定义), 异步限流
│   ├── 调度层: APScheduler (定时爬取) + SummaryQueueManager (后台摘要队列)
│   ├── SCI 分区: JCR 数据种子 + 期刊名模糊匹配
│   └── 静态文件: FastAPI StaticFiles + SPA fallback
│
└─【数据】SQLite (data/papers.db)
    ├── 7 张表: keywords, papers, paper_keywords, summaries,
    │           crawl_logs, app_configs, journals
    └── KV 配置: app_configs 表存储 LLM 配置（key-value）
```

---

## 三、项目文件结构

```
美妙的搜论文网站/
├── .env.example                  # 环境变量模板（LLM_API_KEY 等）
├── README.md                     # 原始 README
├── start.bat                     # 开发/备用启动脚本（相对路径）
├── start-silent.vbs              # 静默启动脚本
├── stop.bat                      # 停止脚本
│
├── backend/
│   ├── run.py                    # ★ 桌面启动入口（pywebview + splash + uvicorn 后台线程）
│   ├── paperfind.spec            # ★ PyInstaller 打包配置
│   ├── build_icon.py             # 图标生成脚本（SVG → ICO）
│   ├── icon.ico                  # 应用图标（5帧: 256/64/48/32/16, 32bpp RGBA）
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py             # Settings (pydantic-settings, .env → settings 对象)
│   │   ├── database.py           # SQLAlchemy async engine + session + init_db
│   │   ├── main.py               # ★ FastAPI app: lifespan, middleware, 路由注册, 静态文件
│   │   ├── rate_limit.py         # slowapi 限流器
│   │   ├── schemas/              # Pydantic 请求/响应 schema
│   │   │   └── keyword.py
│   │   │
│   │   ├── models/               # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py       # 统一导入所有模型
│   │   │   ├── keyword.py        # 关键词表
│   │   │   ├── paper.py          # 论文表 + paper_keywords 关联表
│   │   │   ├── summary.py        # AI 摘要表
│   │   │   ├── crawl_log.py      # 爬取日志表
│   │   │   ├── app_config.py     # KV 配置表 (key, value)
│   │   │   └── journal.py        # 期刊/SCI分区表
│   │   │
│   │   ├── routers/              # FastAPI 路由
│   │   │   ├── __init__.py
│   │   │   ├── keywords.py       # GET/POST/PUT/DELETE /api/keywords + import
│   │   │   ├── papers.py         # GET/PUT/DELETE /api/papers + export + star
│   │   │   ├── crawl.py          # POST /api/crawl (SSE 流式爬取)
│   │   │   ├── summary.py        # POST /api/summary (SSE 流式摘要)
│   │   │   ├── config.py         # GET/PUT /api/config (LLM 配置 CRUD)
│   │   │   └── journals.py       # GET /api/journals (期刊查询)
│   │   │
│   │   ├── services/
│   │   │   ├── crawler/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orchestrator.py   # ★ 爬取调度核心：并发爬取 → 去重 → 过滤 → 入库
│   │   │   │   ├── arxiv.py          # ArXiv API 爬虫
│   │   │   │   ├── semantic_scholar.py  # Semantic Scholar API
│   │   │   │   ├── dblp.py           # DBLP API
│   │   │   │   ├── google_scholar.py # Google Scholar (serpapi)
│   │   │   │   ├── jnu_library.py    # 暨南大学图书馆
│   │   │   │   ├── ieee.py           # IEEE Xplore (桩，is_supported=False)
│   │   │   │   └── acm.py            # ACM DL (桩，is_supported=False)
│   │   │   ├── summarizer.py         # ★ AI 摘要：OpenAI-compatible streaming
│   │   │   ├── summary_queue.py      # ★ 后台摘要队列管理器
│   │   │   ├── scheduler_service.py  # APScheduler：定时爬取 + 定时摘要
│   │   │   └── sci_lookup.py         # SCI 分区查询（JCR CSV + 模糊匹配）
│   │   │
│   │   └── utils/
│   │       └── dedup.py              # 论文去重：generate_paper_key + normalize_title
│   │
│   └── data/
│       └── jcr_seed.csv              # JCR 期刊种子数据（SCI 分区）
│
├── frontend/
│   ├── package.json              # Vite + React + Tailwind + vite-plugin-singlefile
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/
│   │   └── favicon.svg           # 原始 SVG 图标（含滤镜/蒙版）
│   └── src/
│       ├── main.tsx              # React 入口
│       ├── App.tsx               # ★ 路由配置 (HashRouter + CrawlProvider)
│       ├── index.css             # Tailwind + 全局样式
│       ├── api/
│       │   ├── client.ts         # ★ axios 实例 (baseURL: /api, 无 X-Username)
│       │   ├── crawl.ts          # SSE crawl (fetch + ReadableStream)
│       │   ├── papers.ts         # 论文 CRUD + export
│       │   ├── keywords.ts       # 关键词 CRUD
│       │   ├── config.ts         # LLM 配置读写
│       │   └── summary.ts        # SSE 摘要请求
│       ├── contexts/
│       │   └── CrawlContext.tsx   # ★ 全局爬取状态 (startCrawl, isCrawling, eventSource)
│       ├── hooks/
│       │   ├── useKeywords.ts    # 关键词 CRUD hook
│       │   ├── usePapers.ts      # 论文查询 hook
│       │   ├── useSummary.ts     # 摘要请求 hook
│       │   └── useKeywordHistory.ts  # 搜索历史 (localStorage)
│       ├── pages/
│       │   ├── HomePage.tsx      # ★ 论文列表 + 筛选器 + 实时事件
│       │   ├── KeywordsPage.tsx  # 关键词管理 + 搜索历史
│       │   └── SettingsPage.tsx  # LLM 配置 (API Key/URL/Model) + 代理
│       └── components/
│           ├── layout/
│           │   ├── Layout.tsx    # 页面布局 (header + sidebar + content)
│           │   ├── Header.tsx    # 顶部导航栏
│           │   └── Sidebar.tsx   # 左侧筛选栏
│           ├── papers/
│           │   ├── PaperCard.tsx      # 论文卡片
│           │   ├── PaperList.tsx      # 论文列表
│           │   └── PaperDetailModal.tsx  # 论文详情弹窗
│           ├── keywords/
│           │   └── KeywordManager.tsx  # 关键词管理组件
│           ├── common/
│           │   ├── ErrorBoundary.tsx   # React 错误边界
│           │   ├── ErrorMessage.tsx    # 错误提示
│           │   ├── WelcomeModal.tsx    # ★ 首次启动欢迎弹窗 (localStorage)
│           │   └── SummaryProgressBar.tsx  # SSE 摘要进度条
│           └── crawl/
│               └── CrawlPanel.tsx   # 爬取控制面板
│
└── docs/
    └── index.html                # 文档页面
```

---

## 四、数据模型详解

### 4.1 表关系

```
keywords ──┐
           ├── paper_keywords (多对多) ──┐
papers ────┘                           │
  │                                      │
  ├── summaries (一对一, paper_id FK)    │
  └── crawl_logs (无 FK, 日志独立)       │
                                         │
app_configs (KV 配置, 独立)              │
journals (SCI 分区, 独立)                │
```

### 4.2 Keyword（关键词）
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `text` | VARCHAR(500) UNIQUE | 关键词文本，支持中英文 |
| `source` | VARCHAR(50) | 爬取源，默认 "all" |
| `is_active` | BOOLEAN | 是否启用，默认 True |
| `created_at` | DATETIME | |

### 4.3 Paper（论文）
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `title` | TEXT NOT NULL | 论文标题 |
| `authors` | TEXT | JSON 数组字符串 `["Author A", "Author B"]` |
| `abstract` | TEXT | 摘要原文 |
| `publication_date` | DATE | |
| `source` | VARCHAR(100) | 来源爬虫名称 (arxiv/semantic_scholar/...) |
| `source_id` | VARCHAR(200) | 来源平台 ID |
| `doi` | VARCHAR(200) UNIQUE | DOI 唯一约束 |
| `arxiv_id` | VARCHAR(100) UNIQUE | ArXiv ID 唯一约束 |
| `url` | TEXT | 论文 URL |
| `pdf_url` | TEXT | PDF 下载链接 |
| `journal_name` | VARCHAR(500) | 期刊/会议名称 |
| `citation_count` | INTEGER | 引用次数 |
| `year` | INTEGER | 发表年份 |
| `sci_zone` | VARCHAR(10) | SCI 分区 (Q1/Q2/Q3/Q4) |
| `is_starred` | BOOLEAN | 是否星标 |
| `crawled_at` | DATETIME | 抓取时间 |
| `updated_at` | DATETIME | 最后更新时间 |

### 4.4 paper_keywords（多对多关联）
| 字段 | 类型 | 说明 |
|------|------|------|
| `paper_id` | INTEGER FK | |
| `keyword_id` | INTEGER FK | |
| | | 复合主键 (paper_id, keyword_id) |

### 4.5 Summary（AI 摘要）
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `paper_id` | INTEGER FK UNIQUE | 一篇论文一个摘要 |
| `summary_cn` | TEXT | 中文摘要 |
| `key_points_cn` | TEXT | 关键点 |
| `model_used` | VARCHAR(100) | ★ 生成时使用的模型名 |
| `status` | VARCHAR(20) | pending/processing/completed/failed/truncated |
| `source_type` | VARCHAR(20) | abstract/fulltext |
| `source_chars` | INTEGER | 原文字符数 |
| `tokens_used` | INTEGER | 消耗 token 数 |
| `error_message` | TEXT | 失败原因 |
| `created_at` | DATETIME | |
| `updated_at` | DATETIME | |

### 4.6 CrawlLog（爬取日志）
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `status` | VARCHAR(20) | running/success/failed |
| `source` | VARCHAR(50) | 爬取源 |
| `trigger_type` | VARCHAR(20) | manual/scheduled |
| `papers_found` | INTEGER | 爬取到的原始数量 |
| `papers_new` | INTEGER | 新入库数量 |
| `papers_updated` | INTEGER | 更新的数量 |
| `error_message` | TEXT | 错误信息 |
| `started_at` | DATETIME | |
| `finished_at` | DATETIME | |

### 4.7 AppConfig（应用配置 KV）
| 字段 | 类型 | 说明 |
|------|------|------|
| `key` | VARCHAR(100) PK | 配置键 (llm_api_key/llm_base_url/llm_model) |
| `value` | TEXT | 配置值 |

### 4.8 Journal（期刊/SCI 分区）
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `name` | VARCHAR(500) | 期刊名称 |
| `sci_zone` | VARCHAR(10) | Q1/Q2/Q3/Q4 |
| `issn` | VARCHAR(50) | ISSN |

---

## 五、核心业务流程

### 5.1 爬取流程（orchestrator.py → CrawlOrchestrator.run_full_crawl）

```
用户添加关键词
    │
    ▼
POST /api/crawl (SSE)
    │
    ▼
CrawlOrchestrator.run_full_crawl(source, trigger, keyword_ids, event_queue)
    │
    ├─ 1. 查询启用的关键词（指定 IDs 或全部启用）
    │
    ├─ 2. 对每个关键词，并发调用所有支持的爬虫
    │      ├─ ArXiv
    │      ├─ Semantic Scholar
    │      ├─ DBLP
    │      ├─ Google Scholar
    │      ├─ JNU Library
    │      └─ (IEEE/ACM → 桩, 跳过)
    │      │
    │      └─ _safe_crawl: 单个爬虫 try/except，网络错误记录到 unreachable_sources
    │
    ├─ 3. 去重 (generate_paper_key: DOI > arXiv ID > 标题归一化)
    │
    ├─ 4. ★ 关键词匹配过滤 (后过滤)
    │      │  _keyword_matches(title|abstract, keyword.text)
    │      │  英文: re.search(r'\b' + word + r'\b', text) — 全词边界匹配
    │      │  中文: substring match
    │      │  全部: 空格分词，每个词都必须匹配 (AND)
    │      └─ 不匹配的论文从 paper_keyword_map 移除
    │
    ├─ 5. 入库 / 更新
    │      ├─ 新论文: INSERT → 关联所有匹配的关键词
    │      ├─ 已有论文: UPDATE (citation_count, abstract, journal, doi 补全)
    │      └─ event_queue 推送 paper_new 事件 (SSE → 前端实时显示)
    │
    ├─ 6. SCI 分区解析 (bulk_resolve: 期刊名模糊匹配 JCR 数据)
    │
    └─ 7. event_queue 推送 complete 事件 (含 unreachable/unsupported 源信息)
```

### 5.2 AI 摘要流程

```
前端 POST /api/summary/{paper_id} (SSE)
    │
    ▼
Summarizer.summarize_stream(paper_id)
    │
    ├─ 1. 检查是否已有 completed 摘要 (model_used == 当前模型)
    │     └─ 有 → 直接返回 done
    │
    ├─ 2. 获取论文全文
    │     ├─ Abstract 模式: 直接用摘要文本
    │     └─ Fulltext 模式: FulltextExtractor 从 PDF/HTML 提取
    │
    ├─ 3. 构造 prompt (中英文合并提示)
    │
    ├─ 4. 调用 OpenAI-compatible API (流式)
    │     ├─ AsyncOpenAI client
    │     ├─ asyncio.Semaphore(3) 限流
    │     └─ streaming response → yield chunk
    │
    └─ 5. 保存/更新 Summary 记录
          ├─ status: completed/failed/truncated
          ├─ model_used: 记录生成模型
          └─ 前端收到 done 事件
```

### 5.3 后台摘要队列（SummaryQueueManager）

```
lifespan 启动
    │
    ├─ settings.llm_api_key 非空 → 启动 SummaryQueueManager
    │
    └─ 后台 asyncio.Task 循环:
          │
          ├─ _count_remaining(): 统计待处理论文
          │     SELECT COUNT(*) FROM papers
          │     WHERE abstract IS NOT NULL
          │     AND id NOT IN (
          │         SELECT paper_id FROM summaries
          │         WHERE status='processing'
          │            OR (status='completed' AND model_used == settings.llm_model)
          │     )
          │
          ├─ process_batch(batch_size=1, idle_seconds=60):
          │     ├─ _get_next() → 获取下一篇待处理论文
          │     ├─ Summarizer().summarize_stream()
          │     └─ idle 60s 后下一轮
          │
          └─ ★ 关键: 排除条件是 model_used == settings.llm_model
               用户换模型后，旧模型的摘要不再被排除 → 自动重新总结
```

### 5.4 定时任务（scheduler_service.py → APScheduler）

```
init_scheduler() [lifespan 中调用]
    │
    ├─ crawl_job: 每天 08:00 执行 _run_daily_crawl()
    │      └─ CrawlOrchestrator().run_full_crawl(source="all", trigger="scheduled")
    │
    └─ summary_job: 每天 09:00 执行 _run_daily_summary()
           └─ get_summary_queue().process_batch(batch_size=5)
```

---

## 六、前端架构详解

### 6.1 状态管理
- **CrawlContext**: 全局爬取状态（`startCrawl`, `isCrawling`, `eventSource`）
  - SSE EventSource 接收 `paper_new` / `complete` / `error` 事件
  - 新论文自动追加到 HomePage 列表
- **localStorage**: AI 配置（API Key/URL/Model）、搜索历史、欢迎弹窗状态

### 6.2 页面路由
| 路由 | 组件 | 核心功能 |
|------|------|----------|
| `#/` | HomePage | 论文列表 + 左侧筛选栏 + 爬取/摘要进度 |
| `#/keywords` | KeywordsPage | 关键词增删改 + 搜索历史 + 添加即爬取 |
| `#/settings` | SettingsPage | LLM 配置表单 + 代理设置 |

### 6.3 筛选栏（Sidebar）
- 关键词多选（仅显示匹配的关键词）
- 来源多选
- SCI 分区多选
- 时间范围
- 仅星标
- 排序（时间/引用数）

### 6.4 实时事件
前端通过 `EventSource` 从 `/api/crawl` SSE 端点接收：
- `paper_new`: 新论文实时出现在列表顶部
- `complete`: 爬取完成，显示统计
- `error`: 爬取失败消息
- 摘要进度: `SummaryProgressBar` 组件

---

## 七、配置体系

### 7.1 三级配置优先级
```
环境变量 (.env) < 数据库 (app_configs) < 运行时内存 (settings 对象)
```

### 7.2 配置项清单
| 配置键 | 来源 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | .env | `sqlite+aiosqlite:///data/papers.db` | 数据库路径 |
| `LLM_API_KEY` | .env → DB → settings | "" | AI API Key |
| `LLM_BASE_URL` | .env → DB → settings | "" | AI API Base URL |
| `LLM_MODEL` | .env → DB → settings | "" | AI 模型名 |
| `PROXY_URL` | .env → settings | "" | HTTP 代理 |
| `CRAWL_SCHEDULE_HOUR` | .env | 8 | 定时爬取小时 |
| `CRAWL_SCHEDULE_MINUTE` | .env | 0 | 定时爬取分钟 |
| `SUMMARY_BATCH_SIZE` | .env | 5 | 批量摘要大小 |
| `LOG_LEVEL` | .env | INFO | 日志级别 |

### 7.3 配置同步关键逻辑
- **启动时**: `main.py` lifespan 从 DB 加载 LLM 配置覆盖 settings（去掉 `and not settings.xxx` 条件后，DB 值始终优先）
- **保存时**: `config.py` PUT handler 写入 DB 后同步 `settings.llm_*` 到内存
- **运行时**: Summarizer `__init__` 从 settings 读取，每次创建新实例自动获取最新值

---

## 八、项目历史与关键决策

### 8.1 从多用户到单机（第一次重构）
- **原始架构**: 前端 GitHub Pages + 后端 Render.com + X-Username 用户隔离
- **决策**: 放弃云部署，改为 PyInstaller 单文件 .exe，本地 SQLite
- **影响文件**: 删除 `dependencies.py`、`auth.py`、`models/user.py`；所有模型/路由删 `username` 字段

### 8.2 从浏览器到原生窗口（第二次改造）
- **原始**: `webbrowser.open()` 打开系统浏览器 + 终端黑窗
- **决策**: 使用 `pywebview`（Edge WebView2）而非 Electron
  - 优点: 利用系统内置 WebView2，无需打包浏览器内核
  - 缺点: 依赖 Windows 10+ 自带 WebView2 Runtime
- **启动体验**: Splash HTML → JS 轮询服务就绪 → 自动跳转，无终端窗口

### 8.3 AI 配置同步问题（两次修复）
- **第一次修复** (3 files): `config.py` 同步 settings + `summary.py` 读 DB + `main.py` 启动加载
- **第二次修复** (1 file): 去掉 `and not settings.xxx` 条件 → DB 值始终覆盖 .env 默认值
- **影响**: 用户换模型后，后台队列自动重新总结旧论文

### 8.4 关键词匹配演进
1. 原始: 爬虫返回什么就入库什么（无过滤）
2. 问题: "AR" 搜出 "car"、"market" 等无关论文
3. 方案: 英文用正则 `\b` 词边界匹配 + 空格分词 AND 逻辑
4. 中文: 继承英文的空格分词，但用子串匹配（无词边界概念）
5. 后过滤: 入库前对所有论文做标题/摘要关键词匹配

### 8.5 图标问题
- 原始 `favicon.svg` 含 `<filter>` + `<mask>` + `display-p3` → cairosvg 渲染为黑色
- 解决: 提取 `<path d="...">` 创建简化版纯色 SVG → cairosvg → Pillow → 5 帧 ICO
- 窗口图标: Win32 API `FindWindowW` + `LoadImageW` + `WM_SETICON` 显式设置

---

## 九、开发与打包

### 9.1 环境
- Python 3.11+ (conda env `p`)
- Node.js 18+
- Windows 10/11 (依赖 Edge WebView2 Runtime)

### 9.2 开发命令
```bash
# 后端开发
cd backend
python run.py                    # 启动 (pywebview + uvicorn)
# 或仅后端无 GUI:
uvicorn app.main:app --reload --port 8001

# 前端开发
cd frontend
npm run dev                      # Vite dev server (localhost:5173)

# 生成图标（修改颜色/形状后）
cd backend
python build_icon.py
```

### 9.3 打包
```bash
# 1. 构建前端
cd frontend
npm run build                    # → dist/index.html (vite-plugin-singlefile 内联)

# 2. 打包 .exe
cd ../backend
pyinstaller paperfind.spec       # → dist/论文搜搜.exe (~224MB)

# 关键 spec 配置:
#   console=False        → 无终端窗口 (Windows GUI subsystem)
#   icon="icon.ico"      → 嵌入应用图标
#   hiddenimports        → webview + clr_loader + pythonnet + bottle 等
```

### 9.4 发布
分发 `论文搜搜.exe` 即可，用户双击运行。首次启动会在 exe 同目录创建 `data/` 文件夹存放 SQLite 数据库。

---

## 十、已知限制与待改进

| 限制 | 说明 |
|------|------|
| IEEE/ACM 爬虫 | 桩实现 (`is_supported=False`)，需机构 Cookie 认证 |
| WebView2 依赖 | Windows 10 部分旧版本可能没有，需手动安装 WebView2 Runtime |
| 单用户 | 无用户系统，适合个人使用 |
| exe 体积 | ~224MB，主要来自 conda Python + numpy + lxml 等依赖 |
| 无测试 | 当前没有单元测试或集成测试 |
| 前端无热更新 | 打包后前端内联在 exe 中，更新需重新打包 |
| Google Scholar | 依赖 serpapi 付费 API |

---

## 十一、关键代码位置速查

| 场景 | 文件 | 行 |
|------|------|-----|
| 应用入口 | `backend/run.py` | `main()` |
| FastAPI 路由注册 | `backend/app/main.py` | 111-136 |
| 启动时 DB 配置加载 | `backend/app/main.py` | 54-71 |
| 爬取编排 | `backend/app/services/crawler/orchestrator.py` | `run_full_crawl()` |
| 关键词匹配 | `backend/app/services/crawler/orchestrator.py` | 29-41 `_keyword_matches()` |
| 论文去重 | `backend/app/utils/dedup.py` | `generate_paper_key()` |
| AI 摘要流 | `backend/app/services/summarizer.py` | `summarize_stream()` |
| 后台摘要队列 | `backend/app/services/summary_queue.py` | `_count_remaining()`, `_get_next()` |
| LLM 配置读 | `backend/app/routers/config.py` | `get_effective_config()` |
| LLM 配置写 | `backend/app/routers/config.py` | 80-98 |
| Splash 动画 HTML | `backend/run.py` | `SPLASH_HTML` |
| 窗口图标设置 | `backend/run.py` | `_set_window_icon()` |
| 前端路由 | `frontend/src/App.tsx` | 10-27 |
| API client | `frontend/src/api/client.ts` | `apiFetch()` |
| SSE 爬取 | `frontend/src/api/crawl.ts` | `streamCrawl()` |
| 爬取全局状态 | `frontend/src/contexts/CrawlContext.tsx` | `CrawlProvider` |
| 欢迎弹窗 | `frontend/src/components/common/WelcomeModal.tsx` | |
| PyInstaller 打包 | `backend/paperfind.spec` | |
| 图标生成 | `backend/build_icon.py` | |
