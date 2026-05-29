import asyncio
import logging

from sqlalchemy import case, select

from app.config import settings
from app.database import async_session
from app.models.paper import Paper
from app.models.summary import Summary
from app.services.fulltext_extractor import FulltextExtractor
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

CHUNK_SIZE = 6000   # chars per chunk for long texts
CHUNK_OVERLAP = 200  # overlap between chunks to preserve context
MAX_DIRECT_CHARS = 8000  # summarize directly if text is shorter than this
MAX_FULLTEXT_CHARS = 80_000  # truncate fulltext beyond this to avoid OOM
MAX_CHUNKS = 12  # hard cap on number of chunks to prevent runaway memory

# Prompt when using fulltext / HTML
FULLTEXT_PROMPT = """请用中文总结以下学术论文的内容。

内容来源：{source_label}
（注意：如果来源是摘要或元信息，总结深度可能有限。如是全文，请尽量全面总结。）

请包含以下部分：
1. **研究背景与问题**：这篇论文要解决什么问题？
2. **方法**：论文提出了什么方法或模型？
3. **主要发现**：实验或理论分析得出了什么结论？
4. **局限性**：论文提到了哪些限制或不足？

标题：{title}
内容：
{content}

请直接输出，不要额外添加寒暄。"""

# Prompt for summarizing a single chunk of a long paper
CHUNK_PROMPT = """你正在分析一篇较长论文的一个部分。请提取该部分的关键信息，用中文简洁概括。

请关注：
- 这部分讨论了什么问题或方法？
- 有哪些重要结果或论据？

内容：
{chunk_text}

请用3-5句话概括。"""

# Prompt for merging chunk summaries into a final coherent summary
MERGE_PROMPT = """请将以下多个分块摘要整合成一篇完整的论文中文总结。

来源：{source_label}

请包含：
1. **研究背景与问题**
2. **方法**
3. **主要发现**
4. **局限性**

标题：{title}

各分块摘要：
{chunk_summaries}

请直接输出最终总结，不要提及"分块"或"整合"等过程词。"""

# Product-oriented guide prompts. They intentionally override the original
# summary prompts above without touching the rest of the summarization flow.
FULLTEXT_PROMPT = """请用中文为下面这篇学术论文写一份“论文导读”，不是普通摘要。
内容来源：{source_label}
用户研究方向档案：{research_profile}

请按以下结构输出：
1. **一句话结论**：用一句话说明这篇论文最重要的价值。
2. **研究问题**：它想解决什么问题，为什么重要？
3. **方法与数据**：它用了什么方法、模型、实验或数据？
4. **主要发现**：最核心的结论是什么？
5. **创新点**：相比已有工作，它新在哪里？
6. **局限与风险**：有哪些限制、假设或可能不可靠的地方？
7. **与我的方向的关系**：结合研究方向档案判断相关性；如果档案为空，就说明适合哪些研究者阅读。
8. **阅读优先级**：给出“高/中/低”并说明理由。

标题：{title}
内容：{content}

请直接输出导读内容，不要添加额外寒暄。"""

CHUNK_PROMPT = """你正在分析一篇较长论文的一部分。请用中文提取这一部分对最终“论文导读”有用的信息。
重点关注：研究问题、方法、数据、实验结果、创新点、局限。

内容：{chunk_text}

请用 3-5 句话概括。"""

MERGE_PROMPT = """请把以下多个分块摘要整合成完整的中文“论文导读”。
来源：{source_label}
用户研究方向档案：{research_profile}

请按以下结构输出：
1. **一句话结论**
2. **研究问题**
3. **方法与数据**
4. **主要发现**
5. **创新点**
6. **局限与风险**
7. **与我的方向的关系**
8. **阅读优先级**

标题：{title}

各分块摘要：
{chunk_summaries}

请直接输出最终导读，不要提到“分块”或“整合”过程。"""

SOURCE_LABELS = {
    "pdf": "PDF 全文",
    "html": "网页正文",
    "abstract": "摘要（全文不可用）",
    "metadata": "元信息（全文和摘要均不可用，总结仅供参考）",
}


class Summarizer:
    _locks: dict[int, asyncio.Lock] = {}
    _locks_guard = asyncio.Lock()
    _api_semaphore = asyncio.Semaphore(3)

    # User-streaming priority
    _user_streaming_count = 0
    _user_streaming_changed = asyncio.Event()
    _user_streaming_changed.set()
    _stream_count_lock = asyncio.Lock()

    @classmethod
    async def _pause_background(cls):
        async with cls._stream_count_lock:
            cls._user_streaming_count += 1
            if cls._user_streaming_count > 0:
                cls._user_streaming_changed.clear()

    @classmethod
    async def _resume_background(cls):
        async with cls._stream_count_lock:
            cls._user_streaming_count -= 1
            if cls._user_streaming_count <= 0:
                cls._user_streaming_count = 0
                cls._user_streaming_changed.set()

    def __init__(self):
        self._client: AsyncOpenAI | None = None
        self._model = settings.llm_model
        self._api_key = settings.llm_api_key
        self._base_url = settings.llm_base_url
        self._extractor = FulltextExtractor()

    def _get_client(self) -> "AsyncOpenAI":
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "AI 摘要依赖 openai 未安装，请先安装 backend/requirements.txt 中的依赖。"
            ) from exc

        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    async def _get_lock(self, paper_id: int) -> asyncio.Lock:
        async with self._locks_guard:
            if paper_id not in self._locks:
                self._locks[paper_id] = asyncio.Lock()
            return self._locks[paper_id]

    # ---- helpers ----

    async def _get_research_profile(self) -> str:
        try:
            from app.routers.config import get_effective_config

            cfg = await get_effective_config()
            profile = str(cfg.get("research_profile") or "").strip()
            return profile or "未填写"
        except Exception as e:
            logger.warning("Failed to load research profile for prompt: %s", e)
            return "未填写"

    async def _build_prompt(self, paper, content: str, source: str) -> str:
        """Build the summarization prompt based on available content."""
        research_profile = await self._get_research_profile()
        return FULLTEXT_PROMPT.format(
            source_label=SOURCE_LABELS.get(source, source),
            research_profile=research_profile,
            title=paper.title,
            content=content,
        )

    def _split_chunks(self, text: str) -> list[str]:
        """Split text into overlapping chunks for map-reduce summarization."""
        chunks: list[str] = []
        start = 0
        n = len(text)

        if CHUNK_OVERLAP >= CHUNK_SIZE:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

        while start < n:
            end = min(start + CHUNK_SIZE, n)
            chunks.append(text[start:end])

            if end >= n:
                break

            start = end - CHUNK_OVERLAP

        if len(chunks) > MAX_CHUNKS:
            logger.warning(
                "Truncating %d chunks to %d (MAX_CHUNKS)", len(chunks), MAX_CHUNKS
            )
            chunks = chunks[:MAX_CHUNKS]

        return chunks

    async def _summarize_chunk(self, chunk_text: str) -> str:
        """Summarize a single chunk (used in map phase)."""
        prompt = CHUNK_PROMPT.format(chunk_text=chunk_text)
        async with self._api_semaphore:
            response = await self._get_client().chat.completions.create(
                model=self._model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        return response.choices[0].message.content or ""

    async def _summarize_long_text(self, paper, content: str, source: str) -> str:
        """
        Map-reduce for texts too long for a single LLM call.
        1. Split into chunks
        2. Summarize each chunk concurrently (bounded by semaphore)
        3. Merge chunk summaries into final summary
        """
        chunks = self._split_chunks(content)
        logger.info("Paper %d: chunking %d chars into %d chunks", paper.id, len(content), len(chunks))

        # Phase 1: Map — summarize chunks concurrently, preserving order
        async def _summarize_one(i: int, chunk: str) -> str:
            try:
                summary = await self._summarize_chunk(chunk)
                return f"[部分 {i+1}/{len(chunks)}] {summary}"
            except Exception as e:
                logger.warning("Chunk %d failed for paper %d: %s", i, paper.id, e)
                return f"[部分 {i+1}] 提取失败：{e}"

        results = await asyncio.gather(
            *(_summarize_one(i, chunk) for i, chunk in enumerate(chunks)),
            return_exceptions=True,
        )
        chunk_summaries: list[str] = [
            str(r) if not isinstance(r, BaseException) else f"[部分] 提取失败：{r}"
            for r in results
        ]

        if not chunk_summaries:
            raise RuntimeError("All chunks failed to summarize")

        if len(chunk_summaries) == 1:
            return chunk_summaries[0]

        # Phase 2: Reduce — merge all chunk summaries
        merge_prompt = MERGE_PROMPT.format(
            source_label=SOURCE_LABELS.get(source, source),
            research_profile=await self._get_research_profile(),
            title=paper.title,
            chunk_summaries="\n\n---\n\n".join(chunk_summaries),
        )
        async with self._api_semaphore:
            response = await self._get_client().chat.completions.create(
                model=self._model,
                max_tokens=2048,
                messages=[{"role": "user", "content": merge_prompt}],
            )
        return response.choices[0].message.content or ""

    # ---- public methods ----

    @async_retry(max_retries=3, base_delay=2.0, exceptions=(Exception,))
    async def _summarize_with_retry(self, paper_id: int) -> Summary:
        lock = await self._get_lock(paper_id)
        async with lock:
            return await self._summarize_paper_inner(paper_id)

    async def summarize_paper(self, paper_id: int) -> Summary:
        """Summarize a single paper (non-streaming, with fulltext + chunking support)."""
        try:
            return await self._summarize_with_retry(paper_id)
        except Exception as e:
            logger.error("All retries exhausted for paper %d: %s", paper_id, e)
            async with async_session() as db:
                paper = await db.get(Paper, paper_id)
                result = await db.execute(
                    select(Summary).where(Summary.paper_id == paper_id)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.status = "failed"
                    existing.error_message = str(e)[:500]
                    await db.commit()
                else:
                    db.add(Summary(
                        paper_id=paper_id,
                        status="failed",
                        error_message=str(e)[:500],
                    ))
                    await db.commit()
            raise

    async def stream_summarize(self, paper_id: int):
        """Stream AI summary generation with fulltext + chunking support."""
        await Summarizer._pause_background()
        try:
            async for chunk in self._stream_summarize_inner(paper_id):
                yield chunk
        finally:
            await Summarizer._resume_background()

    async def _stream_summarize_inner(self, paper_id: int):
        lock = await self._get_lock(paper_id)
        async with lock:
            async with async_session() as db:
                paper = await db.get(Paper, paper_id)
                if not paper:
                    yield {"type": "error", "message": f"Paper {paper_id} not found"}
                    return

                result = await db.execute(
                    select(Summary).where(Summary.paper_id == paper_id)
                )
                existing = result.scalar_one_or_none()
                if existing and existing.status == "completed" and existing.model_used == self._model:
                    yield {"type": "done", "summary": existing.summary_cn, "source_type": existing.source_type, "source_chars": existing.source_chars}
                    return

                if existing:
                    existing.status = "processing"
                    existing.error_message = None
                    summary = existing
                else:
                    summary = Summary(paper_id=paper_id, status="processing")
                    db.add(summary)
                await db.commit()
                await db.refresh(summary)
                summary_id = summary.id

                # --- Fulltext extraction ---
                ft = await self._extractor.get_best_available_text(paper)
                content = ft["text"]
                source = ft["source"]
                source_chars = ft["source_chars"]

                # Truncate overly long fulltext to avoid OOM
                orig_chars = source_chars
                if source_chars > MAX_FULLTEXT_CHARS and source in ("pdf", "html"):
                    content = content[:MAX_FULLTEXT_CHARS]
                    source_chars = MAX_FULLTEXT_CHARS
                    yield {"type": "status", "message": f"全文过长，已截取前 {MAX_FULLTEXT_CHARS} 字（原 {orig_chars} 字）"}

                yield {"type": "status", "message": f"内容来源: {SOURCE_LABELS.get(source, source)} ({source_chars} 字)", "source_type": source, "source_chars": source_chars}

                # Save source metadata (store original source_chars)
                summary.source_type = source
                summary.source_chars = orig_chars
                await db.commit()

            try:
                full_content: str

                if source_chars > MAX_DIRECT_CHARS:
                    # Long text: chunk → summarize each → merge → stream the merge
                    yield {"type": "status", "message": f"全文较长 ({source_chars} 字)，正在分块分析..."}
                    chunks = self._split_chunks(content)
                    chunk_summaries: list[str] = []
                    for i, chunk in enumerate(chunks):
                        yield {"type": "status", "message": f"正在分析第 {i+1}/{len(chunks)} 部分..."}
                        try:
                            cs = await self._summarize_chunk(chunk)
                            chunk_summaries.append(f"[部分 {i+1}/{len(chunks)}] {cs}")
                        except Exception as e:
                            logger.warning("Chunk %d failed for paper %d (stream): %s", i, paper_id, e)
                            chunk_summaries.append(f"[部分 {i+1}] 提取失败")

                    if len(chunk_summaries) > 1:
                        merge_prompt = MERGE_PROMPT.format(
                            source_label=SOURCE_LABELS.get(source, source),
                            research_profile=await self._get_research_profile(),
                            title=paper.title,
                            chunk_summaries="\n\n---\n\n".join(chunk_summaries),
                        )
                        yield {"type": "status", "message": "正在整合总结..."}
                        async with self._api_semaphore:
                            stream = await self._get_client().chat.completions.create(
                                model=self._model,
                                max_tokens=2048,
                                messages=[{"role": "user", "content": merge_prompt}],
                                stream=True,
                            )
                        full_content = ""
                        async for chunk in stream:
                            if chunk.choices and chunk.choices[0].delta.content:
                                text = chunk.choices[0].delta.content
                                full_content += text
                                yield {"type": "chunk", "text": text}
                    else:
                        full_content = chunk_summaries[0]
                        yield {"type": "chunk", "text": full_content}
                else:
                    # Short enough — stream directly
                    prompt = await self._build_prompt(paper, content, source)
                    async with self._api_semaphore:
                        stream = await self._get_client().chat.completions.create(
                            model=self._model,
                            max_tokens=2048,
                            messages=[{"role": "user", "content": prompt}],
                            stream=True,
                        )
                    full_content = ""
                    async for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            text = chunk.choices[0].delta.content
                            full_content += text
                            yield {"type": "chunk", "text": text}

                # Save completed summary
                async with async_session() as db:
                    summary = await db.get(Summary, summary_id)
                    if summary:
                        summary.summary_cn = full_content
                        summary.key_points_cn = full_content
                        summary.model_used = self._model
                        summary.tokens_used = len(full_content) // 2
                        summary.status = "completed"
                        summary.source_type = source
                        summary.source_chars = source_chars
                        await db.commit()

                yield {"type": "done", "summary": full_content, "source_type": source, "source_chars": source_chars}

            except asyncio.CancelledError:
                async with async_session() as db:
                    summary = await db.get(Summary, summary_id)
                    if summary:
                        summary.status = "failed"
                        summary.error_message = "User cancelled"
                        await db.commit()
                raise
            except Exception as e:
                logger.error("Stream summary failed for paper %d: %s", paper_id, e)
                async with async_session() as db:
                    summary = await db.get(Summary, summary_id)
                    if summary:
                        summary.status = "failed"
                        summary.error_message = str(e)[:500]
                        await db.commit()
                yield {"type": "error", "message": str(e)}

    async def _summarize_paper_inner(self, paper_id: int) -> Summary:
        """Non-streaming inner summary with fulltext + chunking support."""
        # Phase 1: DB operations (read paper, create/update summary record, extract fulltext)
        async with async_session() as db:
            paper = await db.get(Paper, paper_id)
            if not paper:
                raise ValueError(f"Paper {paper_id} not found")

            existing = await db.execute(
                select(Summary).where(Summary.paper_id == paper_id)
            )
            existing = existing.scalar_one_or_none()

            if existing and existing.status == "completed" and existing.model_used == self._model:
                return existing

            if existing:
                existing.status = "processing"
                existing.error_message = None
                summary = existing
            else:
                summary = Summary(paper_id=paper_id, status="processing")
                db.add(summary)

            await db.commit()
            await db.refresh(summary)

            # --- Fulltext extraction ---
            ft = await self._extractor.get_best_available_text(paper)
            content = ft["text"]
            source = ft["source"]
            source_chars = ft["source_chars"]

            # Truncate overly long fulltext to avoid OOM
            orig_chars = source_chars
            if source_chars > MAX_FULLTEXT_CHARS and source in ("pdf", "html"):
                content = content[:MAX_FULLTEXT_CHARS]
                source_chars = MAX_FULLTEXT_CHARS

            # Save source metadata (store original length)
            summary.source_type = source
            summary.source_chars = orig_chars
            await db.commit()
            summary_id = summary.id

        # Phase 2: LLM summarization (outside DB session to avoid greenlet conflicts)
        response = None
        if source_chars > MAX_DIRECT_CHARS:
            full_content = await self._summarize_long_text(paper, content, source)
        else:
            prompt = await self._build_prompt(paper, content, source)
            async with self._api_semaphore:
                response = await self._get_client().chat.completions.create(
                    model=self._model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
            full_content = response.choices[0].message.content or ""

        tokens_used = len(full_content) // 2  # rough estimate
        if response is not None:
            finish_reason = getattr(response.choices[0], "finish_reason", None) if response.choices else None
            is_truncated = (finish_reason == "length")
        else:
            is_truncated = False

        # Phase 3: Save result
        async with async_session() as db:
            summary = await db.get(Summary, summary_id)
            if summary:
                summary.summary_cn = full_content
                summary.key_points_cn = full_content
                summary.model_used = self._model
                summary.tokens_used = tokens_used
                summary.status = "completed" if not is_truncated else "truncated"
                summary.source_type = source
                summary.source_chars = source_chars
                await db.commit()
                await db.refresh(summary)
            return summary

    async def re_summarize_old_models(self, limit: int = 10) -> dict:
        """Re-summarize papers whose summaries were generated with a different model."""
        async with async_session() as db:
            result = await db.execute(
                select(Paper.id)
                .where(
                    Paper.id.in_(
                        select(Summary.paper_id).where(
                            Summary.model_used != self._model,
                            Summary.status == "completed",
                        )
                    )
                )
                .order_by(Paper.citation_count.desc())
                .limit(limit)
            )
            paper_ids = [r[0] for r in result.all()]

        success = 0
        failed = 0
        errors = []

        for pid in paper_ids:
            try:
                await self.summarize_paper(pid)
                success += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                failed += 1
                errors.append({"paper_id": pid, "error": str(e)})
                logger.error("Re-summarize paper %d failed: %s", pid, e)

        return {"success": success, "failed": failed, "errors": errors}

    async def batch_summarize(self, limit: int = 10) -> dict:
        async with async_session() as db:
            zone_order = case(
                (Paper.sci_zone == "Q1", 0),
                (Paper.sci_zone == "Q2", 1),
                (Paper.sci_zone == "Q3", 2),
                (Paper.sci_zone == "Q4", 3),
                else_=4,
            )
            result = await db.execute(
                select(Paper.id)
                .where(Paper.abstract.isnot(None))
                .where(Paper.id.notin_(
                    select(Summary.paper_id).where(Summary.status.in_(["completed", "processing"]))
                ))
                .order_by(zone_order, Paper.citation_count.desc())
                .limit(limit)
            )
            paper_ids = [r[0] for r in result.all()]

        success = 0
        failed = 0
        errors = []

        for pid in paper_ids:
            try:
                await self.summarize_paper(pid)
                success += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                failed += 1
                errors.append({"paper_id": pid, "error": str(e)})
                logger.error("Failed to summarize paper %d: %s", pid, e)

        return {"success": success, "failed": failed, "errors": errors}
