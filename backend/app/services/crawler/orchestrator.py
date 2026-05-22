import asyncio
import logging
import re
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.crawl_log import CrawlLog
from app.models.keyword import Keyword
from app.models.paper import Paper, paper_keywords
from app.services.crawler.arxiv import ArxivCrawler
from app.services.crawler.dblp import DBLPCrawler
from app.services.crawler.acm import ACMLCrawler
from app.services.crawler.ieee import IEEECrawler
from app.services.crawler.semantic_scholar import SemanticScholarCrawler
from app.services.crawler.google_scholar import GoogleScholarCrawler
from app.services.crawler.jnu_library import JNULibraryCrawler

from app.utils.dedup import deduplicate_new_papers, generate_paper_key

logger = logging.getLogger(__name__)

_CJK_RE = re.compile(r'[一-鿿]')


def _keyword_matches(text: str, keyword: str) -> bool:
    """Check if keyword text appears in paper text.
    Words are split by space. Each word must be present.
    English words use whole-word boundary match (e.g. "AR" won't match "car").
    Chinese words use simple substring match."""
    t = text.lower()
    words = keyword.split()
    if _CJK_RE.search(keyword):
        return all(w.lower() in t for w in words)
    return all(
        bool(re.search(r'\b' + re.escape(w.lower()) + r'\b', t))
        for w in words
    )


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


class CrawlOrchestrator:
    def __init__(self):
        self.crawlers = [
            ArxivCrawler(),
            SemanticScholarCrawler(),
            DBLPCrawler(),
            GoogleScholarCrawler(),
            JNULibraryCrawler(),
            IEEECrawler(),
            ACMLCrawler(),
        ]
        self.unreachable_sources: list[dict[str, str]] = []
        self.unsupported_sources: list[str] = []

    async def run_full_crawl(self, source: str = "all", trigger: str = "manual",
                             keyword_ids: list[int] | None = None,
                             event_queue: asyncio.Queue[dict] | None = None) -> CrawlLog:
        log = CrawlLog(status="running", source=source, trigger_type=trigger)
        async with async_session() as db:
            db.add(log)
            await db.commit()
            await db.refresh(log)

        try:
            self.unreachable_sources = []
            self.unsupported_sources = []
            # Collect unsupported crawler names (stubs like IEEE/ACM)
            for c in self.crawlers:
                if not c.is_supported:
                    self.unsupported_sources.append(c.name)
            async with async_session() as db:
                if keyword_ids:
                    keywords = (await db.execute(
                        select(Keyword).where(
                            Keyword.id.in_(keyword_ids),
                            Keyword.is_active == True,
                        )
                    )).scalars().all()
                else:
                    keywords = (await db.execute(
                        select(Keyword).where(
                            Keyword.is_active == True,
                        )
                    )).scalars().all()

            if not keywords:
                log.status = "success"
                log.finished_at = datetime.now(timezone.utc)
                log.error_message = "没有启用的关键词"
                async with async_session() as db:
                    await db.merge(log)
                    await db.commit()
                if event_queue is not None:
                    await event_queue.put({
                        "type": "complete",
                        "papers_found": 0,
                        "papers_new": 0,
                        "papers_updated": 0,
                        "message": "没有启用的关键词，请先添加并启用关键词",
                    })
                return log

            all_papers: list[dict[str, Any]] = []
            paper_keyword_map: dict[str, set[int]] = {}
            for kw in keywords:
                tasks = []
                for crawler in self.crawlers:
                    if source != "all" and crawler.name != source:
                        continue
                    if not crawler.is_supported:
                        continue
                    tasks.append(self._safe_crawl(crawler, kw.text, max_results=100))

                results = await asyncio.gather(*tasks)
                for result in results:
                    for pdata in result:
                        all_papers.append(pdata)
                        key = generate_paper_key(pdata)
                        if key not in paper_keyword_map:
                            paper_keyword_map[key] = set()
                        paper_keyword_map[key].add(kw.id)

                await asyncio.sleep(0.5)

            logger.info("Collected %d raw papers, %d unique by key",
                        len(all_papers), len(paper_keyword_map))

            # Filter: keep only papers whose title/abstract actually matches the keyword
            kw_text_map = {kw.id: kw.text for kw in keywords}
            filtered_papers: list[dict[str, Any]] = []
            removed = 0
            for pdata in all_papers:
                key = generate_paper_key(pdata)
                kw_ids = paper_keyword_map.get(key, set())
                title = pdata.get("title") or ""
                abstract = pdata.get("abstract") or ""
                # Check against trigger keywords only
                if any(_keyword_matches(title, kw_text_map[kw_id])
                       or _keyword_matches(abstract, kw_text_map[kw_id])
                       for kw_id in kw_ids):
                    filtered_papers.append(pdata)
                else:
                    del paper_keyword_map[key]
                    removed += 1
            all_papers = filtered_papers
            if removed:
                logger.info("Filtered %d papers not matching their trigger keywords", removed)

            existing_keys = await self._load_existing_keys()
            unique_papers = deduplicate_new_papers(all_papers, existing_keys)

            papers_added = 0
            papers_updated = 0

            # Load ALL active keywords for cross-linking (not just the trigger keyword)
            async with async_session() as db:
                all_keywords = (await db.execute(
                    select(Keyword).where(Keyword.is_active == True)
                )).scalars().all()
            all_kw_map = {kw.id: kw.text for kw in all_keywords}

            def find_matching_keywords(title: str, abstract: str | None) -> set[int]:
                t = title.lower()
                a = (abstract or "").lower()
                return {kw_id for kw_id, kw_text in all_kw_map.items()
                        if _keyword_matches(t, kw_text) or _keyword_matches(a, kw_text)}

            new_paper_infos: list[dict] = []

            async with async_session() as db:
                for pdata in unique_papers:
                    key = generate_paper_key(pdata)
                    kw_ids = paper_keyword_map.get(key, set())

                    existing = await self._find_existing(db, pdata)
                    if existing:
                        updated = False
                        if pdata.get("citation_count", 0) > (existing.citation_count or 0):
                            existing.citation_count = pdata["citation_count"]
                            updated = True
                        if pdata.get("abstract") and not existing.abstract:
                            existing.abstract = pdata["abstract"]
                            updated = True
                        if pdata.get("journal_name") and not existing.journal_name:
                            existing.journal_name = pdata["journal_name"]
                            updated = True
                        if pdata.get("doi") and not existing.doi:
                            existing.doi = pdata["doi"]
                            updated = True
                        if updated:
                            existing.updated_at = func.now()
                            papers_updated += 1

                        # Link to ALL matching keywords (not just trigger keyword)
                        all_matches = find_matching_keywords(existing.title, existing.abstract)
                        for kw_id in all_matches:
                            await self._link_keyword(db, existing.id, kw_id)
                    else:
                        paper = Paper(
                            title=pdata["title"],
                            authors=pdata.get("authors", "[]"),
                            abstract=pdata.get("abstract"),
                            publication_date=_parse_date(pdata.get("publication_date")),
                            source=pdata["source"],
                            source_id=pdata.get("source_id"),
                            doi=pdata.get("doi"),
                            arxiv_id=pdata.get("arxiv_id"),
                            url=pdata.get("url"),
                            pdf_url=pdata.get("pdf_url"),
                            journal_name=pdata.get("journal_name"),
                            citation_count=pdata.get("citation_count", 0),
                            year=pdata.get("year"),
                        )
                        db.add(paper)
                        await db.flush()
                        papers_added += 1

                        # Link to ALL matching keywords (not just trigger keyword)
                        all_matches = find_matching_keywords(paper.title, paper.abstract)
                        for kw_id in all_matches:
                            await db.execute(
                                paper_keywords.insert().values(paper_id=paper.id, keyword_id=kw_id)
                            )

                        # Collect event info — push after SCI zone resolution
                        matched_kw_texts = [all_kw_map[kw_id] for kw_id in all_matches]
                        new_paper_infos.append({
                            "paper_id": paper.id,
                            "matched_kw_texts": matched_kw_texts,
                            "keyword_ids": list(all_matches),
                        })

                await db.commit()

            from app.services.sci_lookup import bulk_resolve

            async with async_session() as db:
                result = await db.execute(
                    select(Paper.id).where(Paper.sci_zone.is_(None), Paper.journal_name.isnot(None))
                )
                unresolved = [r[0] for r in result.all()]
                if unresolved:
                    resolved_count = await bulk_resolve(unresolved)
                    logger.info("Resolved SCI zones for %d papers", resolved_count)

            # Push paper_new events AFTER SCI zone resolution
            if event_queue is not None and new_paper_infos:
                paper_ids = [info["paper_id"] for info in new_paper_infos]
                async with async_session() as db:
                    result = await db.execute(
                        select(Paper).where(Paper.id.in_(paper_ids))
                    )
                    papers_map = {p.id: p for p in result.scalars().all()}

                for info in new_paper_infos:
                    paper = papers_map.get(info["paper_id"])
                    if paper is None:
                        continue
                    await event_queue.put({
                        "type": "paper_new",
                        "paper": {
                            "id": paper.id,
                            "title": paper.title,
                            "authors": paper.authors,
                            "abstract": paper.abstract,
                            "publication_date": str(paper.publication_date) if paper.publication_date else None,
                            "source": paper.source,
                            "doi": paper.doi,
                            "arxiv_id": paper.arxiv_id,
                            "url": paper.url,
                            "pdf_url": paper.pdf_url,
                            "journal_name": paper.journal_name,
                            "sci_zone": paper.sci_zone,
                            "citation_count": paper.citation_count,
                            "year": paper.year,
                            "is_starred": False,
                            "has_summary": False,
                            "summary_status": "none",
                            "keyword_texts": info["matched_kw_texts"],
                            "keyword_ids": info["keyword_ids"],
                            "crawled_at": str(paper.crawled_at) if paper.crawled_at else None,
                            "updated_at": str(paper.updated_at) if paper.updated_at else None,
                        },
                    })

            log.status = "success"
            log.papers_found = len(all_papers)
            log.papers_new = papers_added
            log.papers_updated = papers_updated
            if event_queue is not None:
                await event_queue.put({
                    "type": "complete",
                    "papers_found": log.papers_found,
                    "papers_new": log.papers_new,
                    "papers_updated": log.papers_updated,
                    "message": f"Crawl completed: {papers_added} new, {papers_updated} updated",
                    "unreachable_sources": self.unreachable_sources,
                    "unsupported_sources": self.unsupported_sources,
                })
        except Exception as e:
            logger.exception("Crawl failed")
            log.status = "failed"
            log.error_message = str(e)
            if event_queue is not None:
                await event_queue.put({
                    "type": "error",
                    "message": str(e),
                })
        finally:
            log.finished_at = datetime.now(timezone.utc)
            async with async_session() as db:
                await db.merge(log)
                await db.commit()

        return log

    async def _link_keyword(self, db: AsyncSession, paper_id: int, keyword_id: int):
        existing = await db.execute(
            select(paper_keywords).where(
                paper_keywords.c.paper_id == paper_id,
                paper_keywords.c.keyword_id == keyword_id,
            )
        )
        if existing.first() is None:
            await db.execute(
                paper_keywords.insert().values(paper_id=paper_id, keyword_id=keyword_id)
            )
 
    async def _safe_crawl(self, crawler, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        try:
            return await crawler.search(keyword, max_results=max_results)
        except Exception as e:
            import httpx
            msg = str(e)
            is_network = any(phrase in msg.lower() or isinstance(e, t)
                           for phrase in ["connection", "dns", "timeout", "resolve", "refused", "unreachable"]
                           for t in [httpx.ConnectError, httpx.TimeoutException, ConnectionError, OSError])
            if is_network:
                logger.warning("Crawler %s unreachable: %s", crawler.name, msg[:200])
                self.unreachable_sources.append({
                    "source": crawler.name,
                    "reason": msg[:200],
                })
            else:
                logger.error("Crawler %s failed for '%s': %s", crawler.name, keyword, msg[:200])
            return []

    async def _load_existing_keys(self) -> set[str]:
        async with async_session() as db:
            result = await db.execute(
                select(Paper.doi, Paper.arxiv_id, Paper.title, Paper.authors)
            )
            keys = set()
            for row in result.all():
                pdata = {
                    "doi": row[0],
                    "arxiv_id": row[1],
                    "title": row[2],
                    "authors": row[3],
                }
                keys.add(generate_paper_key(pdata))
            return keys

    async def _find_existing(self, db: AsyncSession, pdata: dict) -> Paper | None:
        doi = pdata.get("doi")
        if doi:
            result = await db.execute(
                select(Paper).where(Paper.doi == doi)
            )
            p = result.scalar_one_or_none()
            if p:
                return p

        arxiv_id = pdata.get("arxiv_id")
        if arxiv_id:
            result = await db.execute(
                select(Paper).where(Paper.arxiv_id == arxiv_id)
            )
            p = result.scalar_one_or_none()
            if p:
                return p

        title = pdata.get("title", "")
        if title:
            from app.utils.dedup import normalize_title

            nt = normalize_title(title)
            result = await db.execute(select(Paper))
            for p in result.scalars().all():
                if normalize_title(p.title) == nt:
                    return p

        return None
