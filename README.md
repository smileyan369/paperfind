# PaperFind 论文搜搜

PaperFind 是一个面向 Windows 本地使用的论文检索与 AI 导读工具。它可以根据关键词或自然语言研究需求，从多个公开论文来源检索论文，保存到本地 SQLite 数据库，并按 SCI 分区、来源、日期、引用数等条件筛选和排序。

项目目前还处在早期阶段，性能、稳定性和检索覆盖率仍在持续改进。它更适合作为个人科研辅助工具使用，而不是成熟的商业级文献平台。

## 下载

Windows 用户可以在仓库右侧的 **Releases** 页面下载最新版 exe：

[下载最新版 paperfind-windows.exe](https://github.com/smileyan369/paperfind/releases/latest/download/paperfind-windows.exe)

首次运行后，软件会在本机保存数据库、设置、关键词历史和 AI 配置。新版已经尽量把 API Key 和历史数据保存到稳定目录，减少更新 exe 后配置丢失的问题。

## 当前功能

- 关键词管理：添加、删除、启用、停用研究关键词。
- 自然语言检索：输入一句研究需求，自动生成可检索关键词，并可一键加入关键词后立即爬取。
- 多源论文检索：聚合 arXiv、Semantic Scholar、DBLP、Crossref、OpenAlex、PubMed、Europe PMC、Google Scholar、暨大图书馆等来源。
- 中英文检索辅助：中文研究方向会尽量转换成英文检索词，提高英文论文召回率。
- 论文去重与入库：按 DOI、arXiv ID、标题归一化等规则去重。
- SCI 分区匹配：根据本地期刊数据尽量匹配 Q1-Q4，并默认优先展示高分区论文。
- 论文浏览：支持按标题/摘要搜索、来源筛选、日期范围、最低引用数、收藏状态、AI 导读状态筛选。
- AI 导读：配置 OpenAI-compatible API 后，可对论文生成中文导读。
- 自动导读开关：默认关闭，避免无意消耗用户 token。
- 研究档案与科研速递：可以填写研究方向档案，首页显示相关论文或近期研究内容。
- CSV 导出：导出当前筛选结果。
- 本地运行：数据默认保存在本地，不依赖云端账号系统。

## AI 配置说明

本项目不内置任何第三方 API Key。需要 AI 导读或 AI 关键词规划时，请在软件设置页自行填写：

- API Key
- API Base URL
- Model

只要服务兼容 OpenAI Chat Completions API，一般都可以尝试使用，例如 OpenAI、DeepSeek、Groq 或其他兼容服务。

请注意：

- AI 导读会消耗你自己的 token 或额度。
- 自动导读默认关闭，需要手动开启。
- 如果 Base URL 填成官网地址而不是 API 地址，可能会出现 `Request Blocked`、HTML 错误页或连接失败。
- AI 生成内容可能有错误，只能作为阅读辅助，不能替代阅读原文和专业判断。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | React, TypeScript, Vite, Tailwind CSS |
| 后端 | FastAPI, SQLAlchemy Async, SQLite, APScheduler |
| AI | OpenAI-compatible Chat Completions API |
| 桌面打包 | PyWebView, PyInstaller |
| 数据库 | SQLite |

## 本地开发

### 环境要求

- Python 3.10+
- Node.js 18+
- Windows 环境打包 exe 需要 PyInstaller 和 PyWebView

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

### 启动开发环境

后端：

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

前端：

```bash
cd frontend
npm run dev
```

前端开发服务会把 `/api` 请求代理到本地后端。

## 打包 Windows exe

先构建前端：

```bash
cd frontend
npm run build
```

再打包桌面程序：

```bash
cd backend
pyinstaller --clean paperfind.spec
```

打包结果位于：

```text
backend/dist/论文搜搜.exe
```

建议把 exe 上传到 GitHub Releases，而不是直接提交进 Git 仓库。

## 验证

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

## 合规与风险提示

- 本项目用于学习、科研辅助和个人文献管理。
- 不提供绕过验证码、绕过付费墙、破解机构权限或批量下载受版权保护全文的能力。
- 不同论文来源可能有自己的 robots、访问频率、版权和使用条款，请在合法合规范围内使用。
- 公开传播、商业使用或再分发论文信息、PDF、AI 摘要时，请自行确认原始来源的许可要求。
- 本项目仍在早期阶段，可能存在 bug、数据不准确、接口变动导致失败或性能问题，请谨慎使用。

## 项目状态

PaperFind 目前是一个能跑起来的本地科研辅助工具，但还不是完美产品。欢迎通过 Issues 提交问题、建议和改进方向。
