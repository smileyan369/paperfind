# 论文搜搜

论文搜搜是一个本地运行的论文检索、筛选与 AI 摘要工具。项目支持从多个论文来源检索论文，按关键词入库，自动匹配 SCI 分区，并可通过 OpenAI 兼容接口生成中文论文总结。

项目当前主要面向本地桌面使用：前端由 React 构建，后端由 FastAPI 提供接口，数据默认保存在本地 SQLite 数据库中，也可以通过 PyInstaller 打包为 Windows 单文件 exe。

> 下载 Windows 版本：请在仓库右侧的 Releases 页面下载最新版 exe。首次运行会在 exe 所在目录旁创建本地数据文件。

## 主要功能

- 多关键词论文检索与管理
- 支持 arXiv、Semantic Scholar、DBLP、Google Scholar、暨大图书馆等来源
- 论文去重、关键词关联、收藏、已读状态
- SCI Q1-Q4 分区匹配与分区优先排序
- 按标题、摘要、来源、日期、引用数、分区筛选论文
- CSV 导出当前筛选结果
- AI 中文摘要生成，支持 PDF、网页正文、摘要和元信息兜底
- AI 自动摘要开关默认关闭，避免无意消耗用户 token
- 本地配置 API Key，版本更新时尽量保留旧用户配置
- Windows 桌面 exe 打包运行

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | React 19, TypeScript, Vite, Tailwind CSS |
| 后端 | FastAPI, SQLAlchemy Async, SQLite, APScheduler |
| AI | OpenAI-compatible Chat Completions API |
| 桌面打包 | PyWebView, PyInstaller |

## 目录结构

```text
.
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── routers/         # FastAPI 路由
│   │   ├── schemas/         # Pydantic 响应/请求模型
│   │   ├── services/        # 爬虫、摘要、调度、SCI 匹配
│   │   ├── config.py        # 配置与本地数据目录
│   │   ├── database.py      # 异步 SQLite 连接
│   │   └── main.py          # FastAPI 应用入口
│   ├── data/
│   │   └── jcr_seed.csv     # 初始 SCI 分区数据
│   ├── run.py               # Windows 桌面入口
│   ├── paperfind.spec       # PyInstaller 打包配置
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/             # 前端 API 封装
│       ├── components/      # UI 组件
│       ├── contexts/        # 全局状态
│       ├── hooks/           # React hooks
│       ├── pages/           # 页面
│       └── types/           # TypeScript 类型
├── PROJECT_SUMMARY.md
├── PROJECT_IMPROVEMENT_PLAN.md
└── README.md
```

## 本地开发

### 环境要求

- Python 3.10+
- Node.js 18+
- Windows 环境下打包 exe 需要 PyInstaller 与 PyWebView

### 安装依赖

```bash
cd backend
python -m pip install -r requirements.txt
python -m pip install pywebview pyinstaller
```

```bash
cd frontend
npm install
```

### 配置环境变量

复制 `.env.example` 为 `.env`，也可以在软件的设置页中配置 AI 接口。

```bash
copy .env.example .env
```

常用 AI 配置示例：

```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

也可以使用其他 OpenAI 兼容服务，例如 OpenAI、Groq、硅基流动等。请确保 `LLM_BASE_URL`、`LLM_MODEL` 与 API Key 属于同一个服务商。

### 启动开发环境

后端默认使用 `8001` 端口：

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

前端开发服务器：

```bash
cd frontend
npm run dev
```

浏览器访问 Vite 输出的本地地址，前端会把 `/api` 请求代理到 `http://localhost:8001`。

## 打包 Windows exe

先构建前端：

```bash
cd frontend
npm run build
```

再打包后端桌面入口：

```bash
cd backend
pyinstaller --clean paperfind.spec
```

打包结果位于：

```text
backend/dist/论文搜搜.exe
```

注意：`backend/dist/`、`backend/build/`、数据库文件和日志属于本地生成产物，不建议提交到 Git。建议把 exe 上传到 GitHub Releases 供用户下载。

## 常见问题

### AI 摘要显示 Request Blocked 或 HTML 错误

这通常说明 AI 服务返回了网页拦截页，而不是正常的 API 响应。请检查：

- `LLM_BASE_URL` 是否为 API 地址，而不是官网地址
- API Key 是否属于当前服务商
- 模型名是否正确
- 网络、代理或服务商风控是否拦截请求

### 为什么自动摘要默认关闭？

自动摘要会持续消耗 API token。为了避免用户无意产生费用，本软件默认关闭自动摘要，需要在设置页手动开启。

### 为什么检索完成后按分区排序？

论文列表以后端 `/api/papers` 返回结果为准，默认按 `Q1 → Q2 → Q3 → Q4 → 未收录` 排序，保证检索完成后优先展示高分区论文。

## AI 与合规说明

本项目包含 AI 摘要功能和论文来源检索功能，使用前请注意以下事项：

- 本软件不会内置任何第三方 AI API Key。用户需要自行在设置页或 `.env` 中配置自己的 API Key。
- AI 摘要会消耗用户所配置服务商的 token 或额度，自动摘要默认关闭，需要用户自行开启。
- AI 生成内容可能存在错误、遗漏、幻觉或理解偏差，只能作为辅助阅读参考，不能替代阅读原文或专业判断。
- 请勿把涉密、敏感、受保护或无权处理的内容提交给第三方 AI 服务。
- 使用 DeepSeek、OpenAI、Groq、硅基流动等服务时，请自行遵守对应服务商的服务条款、隐私政策、计费规则和适用法律法规。
- 本项目会从公开论文来源或用户可访问的网页检索信息。不同网站可能有自己的 robots、访问频率、版权和使用条款，请在合法合规范围内使用。
- 本项目不提供规避验证码、绕过付费墙、破解机构权限或批量下载受版权保护全文的能力。IEEE/ACM 等机构访问需要用户拥有合法机构权限和 Cookie。
- 导出的论文信息、AI 摘要和本地数据库仅供学习、科研辅助和个人管理使用。公开传播、商业使用或再分发时，请自行确认原始论文和数据来源的许可要求。
- 本项目仍处于早期阶段，可能存在 bug、数据不准确、接口变更导致的失败或性能问题，请谨慎使用。

## 开发验证

前端构建：

```bash
cd frontend
npm run build
```

后端测试：

```bash
cd backend
python -m unittest discover -s tests -v
```

## 说明

本项目用于本地论文检索与辅助阅读。不同论文来源可能存在访问频率限制、验证码、网络不可达或接口变更，爬取结果会受当前网络环境影响。
