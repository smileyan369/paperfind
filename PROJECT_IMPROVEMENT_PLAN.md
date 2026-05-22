# PaperFind 后续修正与改进计划

> 本文档用于记录当前项目已经发现的问题、风险点和后续改造方案。目标是让 PaperFind 从“勉强可用的本地 exe 工具”逐步变成稳定、可升级、可维护、对用户费用和数据都安全的桌面应用。

## 一、总体目标

PaperFind 当前定位是 Windows 本地桌面应用：

- 用户双击 exe 即可运行。
- 前端通过 pywebview / WebView2 展示。
- 后端 FastAPI 运行在本地端口。
- 数据保存在本地 SQLite 数据库。
- 用户可通过关键词检索论文、筛选论文、收藏论文、生成 AI 中文摘要。

后续改造的核心原则：

1. 优先保证本地 exe 启动稳定、错误可诊断。
2. 优先保护老用户数据和配置，特别是 API Key、历史摘要、历史论文。
3. 默认不自动消耗用户 token，所有可能产生费用的行为都应由用户明确开启。
4. 爬取、摘要、配置、数据库升级都要可追踪、可恢复。
5. 先修稳定性和升级兼容，再做新功能。

## 二、最高优先级问题

### 1. 历史摘要统计在版本或模型变化后显示异常

#### 问题描述

当前“总结论文数量 / 摘要进度条”可能只统计当前模型或当前 API 配置下生成的摘要。

如果出现以下情况：

- 用户升级版本。
- 用户换了模型。
- 用户的 AI API 配置丢失。
- 后端当前 `settings.llm_model` 为空或不同于旧摘要的 `model_used`。

那么旧的摘要数据仍然在数据库中，但进度条可能显示“已总结 0 篇”。

#### 影响

- 用户会误以为历史摘要丢失。
- 设置页和首页统计不一致。
- 版本升级后信任感下降。

#### 修改方案

后端摘要统计应区分两类指标：

- `total_summarized_any_model`：任何模型生成过且状态为 `completed` 的摘要数量。
- `total_summarized_current_model`：当前模型生成且状态为 `completed` 的摘要数量。

进度条默认显示 `total_summarized_any_model`，因为用户关心的是“已经有摘要的论文数量”，而不是“当前模型摘要数量”。

如果后续需要提示用户“有旧模型摘要可重新生成”，再单独显示：

- `outdated_summary_count`
- `current_model_summary_count`

#### 涉及文件

- `backend/app/services/summary_queue.py`
- `backend/app/routers/summary.py`
- `frontend/src/components/common/SummaryProgressBar.tsx`
- `frontend/src/pages/HomePage.tsx`

#### 验收标准

- 换模型后，旧摘要仍计入“已总结”。
- API Key 为空时，旧摘要仍计入“已总结”。
- 进度条不会因为模型变化显示 0。
- 如果存在旧模型摘要，系统可以另行提示“可重新总结”，但不能把它当作未总结。

### 2. 老用户 API 配置升级后可能丢失

#### 问题描述

当前项目经历过从 `.env`、localStorage、数据库配置等多种配置方式的演进。升级版本后，老用户 API Key 可能存在以下位置：

- 前端 `localStorage`
- 后端 `app_config` 表
- `.env`
- 运行时 `settings`

如果新版本只读取其中一种来源，就可能导致老用户升级后 AI 配置消失。

#### 影响

- 用户升级后 AI 功能突然不可用。
- 用户需要重新输入 API Key。
- 如果用户忘记原 Key，会造成实际使用中断。

#### 修改方案

建立明确的配置迁移和优先级：

1. 后端数据库 `app_config` 是最终事实来源。
2. 启动时后端从 DB 加载配置到 `settings`。
3. 前端启动时调用 `/api/config` 获取后端配置状态。
4. 为兼容老版本，如果前端 localStorage 中存在旧配置，且后端没有配置，则自动调用 `/api/config` 写回 DB。
5. 写回成功后，前端继续以后端返回结果为准。
6. localStorage 只作为迁移来源或临时缓存，不再作为 AI 是否可用的唯一判断依据。

当前代码中的配置表名是 `app_config`，不是 `app_configs`。后续文档、迁移脚本、诊断信息和测试都应统一使用 `app_config`。

API Key 迁移必须避免误覆盖：

- `/api/config` 返回的是脱敏 Key，例如 `****1234`，不能把这类 mask 值写回数据库。
- 只有 localStorage 中保存的是完整 API Key 时，才允许作为迁移来源。
- 如果后端 DB 已经存在 API Key，前端旧 localStorage 不允许覆盖后端配置。
- 如果 localStorage 只有 base URL / model，而后端已有 API Key，可只补全非敏感字段，但仍应以后端已有 Key 为准。

建议增加配置项：

- `config_schema_version`
- `llm_api_key`
- `llm_base_url`
- `llm_model`
- `auto_summary_enabled`

同时建议在迁移中将 `app_config.value` 从当前 `String(500)` 升级为可保存长文本的 `Text` 类型，避免后续保存加密 Key、DPAPI/Credential Manager 引用或 JSON 配置时长度不足。

#### 涉及文件

- `backend/app/routers/config.py`
- `backend/app/models/app_config.py`
- `frontend/src/api/client.ts`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/App.tsx` 或新增配置初始化 hook

#### 验收标准

- 老版本 localStorage 中有 API Key，新版本启动后能迁移到 DB。
- DB 中有 API Key，前端刷新后仍显示 AI 可用。
- 清空浏览器 localStorage 后，只要 DB 有配置，AI 仍可用。
- 用户升级版本后无需重新配置 API Key。

### 3. 自动摘要默认开启会消耗用户 token

#### 问题描述

当前逻辑接近于：只要配置了 LLM API Key，后台摘要队列就会自动运行。

这会导致用户只是填写 API Key 后，系统可能自动为大量论文生成摘要，持续消耗 token 或余额。

#### 影响

- 用户费用不可控。
- 本地程序后台变慢。
- API 限流或欠费后产生大量失败记录。
- 用户对软件失去信任。

#### 修改方案

新增配置项：

```text
auto_summary_enabled = false
```

默认关闭。

行为规则：

- 手动点击某篇论文的“AI 总结”：始终允许，只要 API Key 可用。
- 后台自动总结：只有 `llm_api_key` 存在且 `auto_summary_enabled == true` 时运行。
- 定时爬取后自动总结：同样受 `auto_summary_enabled` 控制。
- 升级老版本时，默认写入 `false`，避免升级后突然开始消耗 token。
- 设置页打开开关后，应立即启动后台摘要队列，不要求用户重启软件。
- 设置页关闭开关后，应立即停止后台摘要队列，并停止继续领取新任务。
- 用户修改 API Key、Base URL 或模型后，也应重新判断摘要队列是否需要启动、停止或重建 Summarizer。

设置页增加开关：

```text
自动生成 AI 摘要
开启后，系统会在后台调用 AI 为待处理论文生成摘要，可能产生 API 费用。
```

欢迎界面也需要增加明确提醒文案：

```text
本软件提供自动总结，但考虑到可能会消耗 token，因此烦请在设置中自行开启。
```

该提醒应出现在首次启动欢迎弹窗中，避免用户误以为配置 API Key 后系统会自动总结，或误开启后不清楚 token 消耗来源。

#### 涉及文件

- `backend/app/routers/config.py`
- `backend/app/main.py`
- `backend/app/services/summary_queue.py`
- `backend/app/services/scheduler_service.py`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/components/common/SummaryProgressBar.tsx`
- `frontend/src/components/common/WelcomeModal.tsx`

#### 验收标准

- 新安装默认不会自动总结。
- 用户手动总结不受自动摘要开关影响。
- 设置页开关关闭时，后台队列不自动消费 API。
- 设置页开关开启后，后台队列才开始处理。
- 定时任务不会绕过该开关。
- 开关状态变化即时生效，不需要重启 exe。

## 三、稳定性与本地 exe 体验

### 4. exe 启动缺少可靠错误处理

#### 问题描述

当前 `backend/run.py` 固定使用 `127.0.0.1:8001` 启动 uvicorn。如果端口被占用、后端启动失败、数据库损坏或依赖异常，用户只会看到启动超时，且没有明显日志。

#### 修改方案

启动流程应增强：

1. 启动前检测端口是否可用。
2. 如果 8001 被占用：
   - 判断是否是同一个 PaperFind 实例。
   - 如果是，直接连接已有实例。
   - 如果不是，自动选择备用端口或提示错误。
3. 增加单实例锁，避免重复启动多个 exe。
4. 增加文件日志：
   - `data/logs/app.log`
   - `data/logs/error.log`
   - 保留最近若干天。
5. 后端线程异常要写入日志，并在 splash 页面显示友好错误。
6. 关闭窗口时尽量优雅停止 uvicorn、scheduler、summary queue。

#### 涉及文件

- `backend/run.py`
- `backend/app/main.py`
- `backend/app/utils/logger.py`

#### 验收标准

- 端口占用时不会无限启动失败。
- 启动失败时用户能看到明确错误。
- exe 无控制台运行时，仍然能在日志文件中定位问题。
- 重复双击 exe 不会启动多个互相抢端口的实例。

### 5. 缺少数据库迁移机制

#### 问题描述

当前数据库初始化主要依赖 `Base.metadata.create_all()`。它能创建新表，但不能可靠更新已有表结构。

当后续新增字段，例如：

- `auto_summary_enabled`
- `search_terms`
- `translation_enabled`
- 新索引

老用户数据库不会自动升级，可能导致运行时报错。

#### 修改方案

添加轻量迁移机制。

建议新增表：

```text
schema_migrations
- version
- applied_at
- description
```

启动时执行迁移：

1. 先通过 `Base.metadata.create_all()` 或等价逻辑确保基础表存在。
2. 检查当前 schema version。
3. 对旧表使用 `PRAGMA table_info(table_name)` 检查字段是否存在。
4. 缺字段使用 `ALTER TABLE ... ADD COLUMN ...`，不要假设老用户数据库结构完整。
5. 缺索引用 `CREATE INDEX IF NOT EXISTS ...`。
6. 按顺序执行未执行过的迁移 SQL。
7. 每个迁移幂等，支持重复启动。
8. 迁移前备份数据库：
   - `data/backups/papers_YYYYMMDD_HHMMSS.db`

第一批迁移应覆盖：

- 配置项迁移。
- 自动摘要开关默认值。
- 双语检索字段。
- 常用索引。

#### 涉及文件

- `backend/app/database.py`
- 新增 `backend/app/migrations/`
- `backend/app/models/app_config.py`

#### 验收标准

- 老数据库升级后不报缺字段错误。
- 迁移失败时保留原数据库备份。
- 新版本可以识别旧版本 DB 并自动升级。
- 重复启动应用不会重复插入配置、重复建索引或破坏已有数据。

## 四、爬取与实时状态

### 6. 爬取 SSE 当前不是真正实时

#### 问题描述

目前 `/api/crawl/stream` 的事件总线会先等待整个 `orchestrator.run_full_crawl()` 完成，然后才读取队列中的事件。这样 `paper_new` 并不是真正边爬边推送。

#### 影响

- 长时间爬取时前端像卡死。
- 新论文不能及时显示。
- 用户不知道程序是否还在工作。

#### 修改方案

应让 orchestrator 和 SSE stream 并行工作：

1. `CrawlEventBus` 启动后台 crawl task。
2. 同时启动一个转发 task，持续从 `event_queue` 读取事件并 broadcast。
3. `paper_new` 产生后立即推送给前端。
4. `complete/error` 事件推送后结束当前 crawl。

#### 涉及文件

- `backend/app/routers/crawl.py`
- `backend/app/services/crawler/orchestrator.py`
- `frontend/src/contexts/CrawlContext.tsx`

#### 验收标准

- 爬取过程中前端能实时收到新论文。
- 页面刷新后能重新连接当前爬取状态。
- 爬取结束后状态可靠变为完成。

### 7. 爬取需要增量策略

#### 问题描述

当前每次爬取都会对每个关键词、每个来源拉较多结果，容易重复请求旧数据。

#### 修改方案

增加关键词来源级别的爬取状态：

```text
keyword_source_states
- keyword_id
- source
- last_crawled_at
- last_success_at
- last_error
- failure_count
- last_result_count
```

增量策略：

- 默认只抓最近一段时间或前几页。
- 手动“深度检索”时才扩大范围。
- 连续失败的源短时间内跳过或降低频率。

#### 涉及文件

- `backend/app/services/crawler/orchestrator.py`
- `backend/app/models/`
- `backend/app/routers/crawl.py`
- `frontend/src/pages/SettingsPage.tsx`

#### 验收标准

- 重复点击爬取不会大量重复请求。
- 设置页能看到每个源最近状态。
- 失败源不会拖慢整个爬取流程。

## 五、双语关键词检索

### 8. 关键词需要支持中英文双向扩展检索

#### 问题描述

有些用户输入中文关键词，但中文论文或中文元数据较少，只查中文会导致结果很少。

同样，用户输入英文关键词时，也可能希望同时查中文翻译，以获得中文论文或中文数据库结果。

#### 目标行为

用户输入中文：

```text
增强现实
```

系统检索：

```text
增强现实
augmented reality
```

用户输入英文：

```text
augmented reality
```

系统检索：

```text
augmented reality
增强现实
```

检索结果统一去重，并关联到用户原始关键词。

#### 修改方案

将关键词从单个字符串升级为：

```text
原始关键词 + 检索词集合
```

建议第一版字段：

```text
keywords.search_terms TEXT
```

保存 JSON 数组：

```json
["增强现实", "augmented reality"]
```

也可后续升级为结构化 JSON：

```json
[
  {"text": "增强现实", "lang": "zh", "source": "original"},
  {"text": "augmented reality", "lang": "en", "source": "translated"}
]
```

爬取逻辑从：

```text
keyword.text -> crawlers
```

改为：

```text
keyword.search_terms -> crawlers
```

所有结果仍关联到原始 `keyword.id`。

爬取后的相关性过滤也必须升级：

- 当前 `_keyword_matches(title|abstract, keyword.text)` 不能只检查原始关键词。
- 改造后应检查 `keyword.search_terms` 中的任意检索词。
- 中文原词触发英文检索时，英文论文只要匹配英文扩展词，就应保留并关联原始中文关键词。
- 英文原词触发中文检索时，中文论文只要匹配中文扩展词，也应保留并关联原始英文关键词。

跨关键词自动关联也必须使用 `search_terms`：

- 新论文入库后，系统会尝试关联所有 active keyword。
- 这一步也要用每个关键词的全部 `search_terms` 做匹配。
- 否则扩展检索搜到的论文可能只关联触发关键词，无法正确关联其它相关关键词。

#### 翻译策略

为了避免额外 token 消耗，建议分阶段实现：

第一阶段：

- 支持手动填写/编辑双语检索词。
- 不自动调用 AI。

第二阶段：

- 增加按钮“生成双语检索词”。
- 用户点击后才调用 AI 或翻译服务。
- 翻译结果保存进数据库。

第三阶段：

- 设置页增加“添加关键词时自动生成双语检索词”开关。
- 默认关闭。

#### 注意事项

- 不要默认加入短缩写，例如 `AR`，避免匹配到 `car`、`market` 等无关结果。
- 英文短语应优先使用完整表达。
- 中文和英文搜索结果统一去重。
- 前端关键词列表展示原始关键词，扩展词作为辅助信息展示。

#### 涉及文件

- `backend/app/models/keyword.py`
- `backend/app/schemas/keyword.py`
- `backend/app/routers/keywords.py`
- `backend/app/services/crawler/orchestrator.py`
- `frontend/src/components/keywords/KeywordManager.tsx`
- `frontend/src/pages/KeywordsPage.tsx`

#### 验收标准

- 中文关键词能同时用中文和英文检索。
- 英文关键词能同时用英文和中文检索。
- 用户能查看和编辑扩展检索词。
- 扩展检索不会产生重复论文。
- 扩展词不会污染原始关键词管理。
- 英文扩展词搜到的论文不会因为不匹配中文原始词而被过滤掉。
- 新论文与所有相关关键词的自动关联会同时考虑原始词和扩展词。

## 六、性能优化

### 9. SQLite 查询和去重需要优化

#### 问题描述

当前存在多处可能全表扫描：

- 标题去重遍历所有论文。
- SCI 匹配每篇论文加载全部期刊。
- 列表筛选、统计、导出缺少索引。

#### 修改方案

增加常用索引：

- `papers.doi`
- `papers.arxiv_id`
- `papers.source`
- `papers.sci_zone`
- `papers.publication_date`
- `papers.citation_count`
- `papers.is_starred`
- `summaries.paper_id`
- `summaries.status`
- `paper_keywords.keyword_id`
- `paper_keywords.paper_id`
- `keywords.is_active`

增加规范化字段：

- `papers.normalized_title`
- `journals.normalized_name`

去重和 SCI 匹配优先查规范化字段，避免反复 Python 全表遍历。

#### 涉及文件

- `backend/app/models/paper.py`
- `backend/app/models/journal.py`
- `backend/app/utils/dedup.py`
- `backend/app/services/sci_lookup.py`
- 数据库迁移脚本

#### 验收标准

- 数据量增加后列表查询仍流畅。
- 爬取去重不再明显变慢。
- SCI 匹配不再对每篇论文加载全部期刊。

### 10. 全文提取网络层需要统一

#### 问题描述

爬虫请求使用了 `settings.proxy_url`，但全文 PDF/HTML 下载可能没有统一使用代理、重试、超时和错误分类。

#### 修改方案

建立统一 HTTP 客户端工具：

- 支持代理。
- 统一 User-Agent。
- 统一 timeout。
- 统一重试。
- 统一错误分类。
- 限制下载大小。

全文提取、爬虫都使用同一网络层。

#### 涉及文件

- `backend/app/services/fulltext_extractor.py`
- `backend/app/services/crawler/base.py`
- 新增 `backend/app/utils/http_client.py`

#### 验收标准

- 设置代理后，爬虫和全文下载都走代理。
- PDF 下载失败时错误可记录。
- 不会因为超大 PDF 卡死或占用大量内存。

## 七、前端状态与体验

### 11. 前端 AI 可用状态应以后端为准

#### 问题描述

当前部分页面通过 `getLlmConfig()` 从 localStorage 判断 `aiAvailable`。这会和后端真实配置不一致。

#### 修改方案

新增全局配置状态：

- `ConfigProvider`
- 或 `useAppConfig`

启动时请求 `/api/config`。

所有页面使用同一个配置状态：

- `ai_available`
- `llm_base_url`
- `llm_model`
- `auto_summary_enabled`

#### 涉及文件

- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/components/papers/PaperCard.tsx`
- `frontend/src/components/papers/PaperDetailModal.tsx`

#### 验收标准

- DB 有 API Key 时，前端所有页面都认为 AI 可用。
- 修改设置后，无需刷新页面即可同步状态。
- localStorage 清空不影响后端已有配置。

### 12. 论文列表、摘要状态、统计需要统一刷新

#### 问题描述

当前首页列表、详情弹窗、摘要进度条、统计数据各自刷新，容易出现状态不一致。

#### 修改方案

建立统一更新策略：

- 摘要完成后，更新当前论文卡片状态。
- 同步刷新统计。
- 如果详情弹窗里生成摘要，列表也立即变为已摘要。
- 如果后台队列完成摘要，前端轮询或 SSE 后更新列表。

#### 涉及文件

- `frontend/src/hooks/usePapers.ts`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/components/papers/PaperDetailModal.tsx`
- `frontend/src/components/common/SummaryProgressBar.tsx`

#### 验收标准

- 卡片、详情、统计、进度条显示一致。
- 摘要完成后不用刷新页面即可看到状态变化。

## 八、安全与用户数据保护

### 13. API Key 存储需要更安全

#### 问题描述

API Key 当前可能以明文形式保存在 DB 或 localStorage。

#### 修改方案

短期：

- 尽量避免 localStorage 长期保存完整 Key。
- 设置页只显示 mask。
- `/api/config` 不返回完整 Key。

中期：

- Windows 下使用 DPAPI 或 Credential Manager 保存 Key。
- DB 中保存加密后的 Key 或保存凭据引用。

#### 涉及文件

- `backend/app/routers/config.py`
- `frontend/src/api/client.ts`
- `frontend/src/pages/SettingsPage.tsx`

#### 验收标准

- 前端接口不暴露完整 API Key。
- localStorage 不再作为长期 Key 存储。
- 用户升级后 Key 仍可用。

### 14. 数据库备份与诊断包

#### 修改方案

设置页增加：

- 打开数据目录。
- 打开日志目录。
- 导出诊断包。
- 备份数据库。

诊断包包含：

- 最近日志。
- 配置摘要，不包含完整 API Key。
- 数据库 schema version。
- 应用版本。
- 最近爬取日志。

#### 涉及文件

- `backend/app/routers/config.py`
- 新增诊断路由
- `frontend/src/pages/SettingsPage.tsx`

#### 验收标准

- 用户反馈问题时可以导出诊断包。
- 诊断包不泄露完整 API Key。

## 九、测试与质量保障

### 15. 补充核心测试

#### 优先测试范围

后端纯逻辑：

- 关键词匹配。
- 中英文扩展检索词生成和解析。
- 论文去重。
- SCI 期刊匹配。
- 配置优先级。
- 摘要统计。
- 自动摘要开关。

后端集成：

- `/api/config`
- `/api/summary/progress`
- `/api/crawl/stream`
- 数据库迁移。

前端：

- 设置页配置保存。
- 自动摘要开关。
- 关键词扩展词编辑。
- 进度条显示旧摘要。

#### 涉及文件

- `backend/tests/`
- 可新增 `frontend` 测试配置

#### 验收标准

- 后续修改核心逻辑时能快速发现回归。
- 版本升级相关逻辑有测试覆盖。

### 16. 每完成一个功能必须执行验证

#### 要求

后续每完成一个功能或修复一个 bug，都必须执行对应的单元测试、构建检查或最小功能验证，确认代码没有明显问题、功能能正常运行。

命令执行规范：

- 每次命令都显式进入绝对路径，不依赖上一次命令留下的工作目录。
- PowerShell 环境中使用 `Set-Location -LiteralPath '绝对路径'; command`。
- 不分两次调用先进入目录再执行命令。

示例：

```powershell
Set-Location -LiteralPath 'C:\Users\lenovo\Desktop\美妙的搜论文网站\backend'; python -m pytest tests -v
Set-Location -LiteralPath 'C:\Users\lenovo\Desktop\美妙的搜论文网站\frontend'; npm run build
Set-Location -LiteralPath 'C:\Users\lenovo\Desktop\美妙的搜论文网站'; git status
```

不同类型改动的最低验证要求：

- 后端纯逻辑：运行对应 pytest；如果暂时没有测试，至少新增/补充相关测试。
- 后端接口：运行接口相关测试，必要时启动本地服务做最小请求验证。
- 数据库迁移：准备旧结构测试库，验证迁移前后数据保留、字段存在、重复迁移安全。
- 前端改动：运行 `npm run build`，涉及 UI 状态时至少做一次本地页面验证。
- exe 启动相关：验证后端能启动、日志能生成、端口冲突或失败路径有可见提示。
- 配置/API Key 相关：验证不会把脱敏 Key 写回 DB，不会用旧 localStorage 覆盖后端已有完整配置。

## 十、建议实施顺序

### 阶段 1：保护用户数据和费用

1. 修复历史摘要统计。
2. 增加自动摘要开关，默认关闭。
3. 修复 API 配置升级保留。
4. 前端 AI 可用状态以后端为准。

### 阶段 2：稳定 exe 运行

1. 启动日志。
2. 端口检测。
3. 单实例锁。
4. 启动失败友好提示。
5. 关闭时优雅停止后台任务。

### 阶段 3：数据库升级能力

1. 增加 schema migration。
2. 增加数据库备份。
3. 添加必要字段和索引。

### 阶段 4：爬取体验和性能

1. 修复真正实时 SSE。
2. 增加爬取源状态。
3. 增加增量爬取。
4. 优化去重和 SCI 匹配。

### 阶段 5：双语关键词检索

1. 增加 `search_terms`。
2. 支持手动编辑中英文检索词。
3. 爬虫按检索词集合查询。
4. 可选增加“生成双语检索词”按钮。

### 阶段 6：测试、诊断和打包优化

1. 补核心测试。
2. 增加诊断包。
3. 优化 PyInstaller 体积和启动速度。

## 十一、暂不建议优先做的事项

以下事项可以做，但不建议排在前面：

- IEEE / ACM 完整爬虫接入。
- 大规模 UI 重做。
- 多用户系统。
- 云端同步。
- 复杂推荐系统。

当前阶段最重要的是：

```text
升级不丢数据、不乱花 token、启动可诊断、统计可信、爬取状态真实。
```
