import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.config import settings
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    name: str = "base"
    base_url: str = ""
    is_supported: bool = True  # Set False for stub/unimplemented crawlers

    def __init__(self, semaphore: asyncio.Semaphore | None = None):
        self.semaphore = semaphore or asyncio.Semaphore(settings.crawl_rate_limit_rps)

    @abstractmethod
    async def search(self, keyword: str, max_results: int = 50) -> list[dict[str, Any]]:
        ...

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError, ConnectionError))
    async def _request(self, url: str, params: dict | None = None) -> httpx.Response:
        proxy = settings.proxy_url or None
        async with self.semaphore:
            async with httpx.AsyncClient(timeout=30.0, proxy=proxy) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp

    def _to_paper_data(
        self,
        title: str = "",
        authors: list[str] | None = None,
        abstract: str | None = None,
        publication_date: str | None = None,
        source: str = "",
        source_id: str | None = None,
        doi: str | None = None,
        arxiv_id: str | None = None,
        url: str | None = None,
        pdf_url: str | None = None,
        journal_name: str | None = None,
        citation_count: int = 0,
        year: int | None = None,
    ) -> dict[str, Any]:
        import json

        return {
            "title": title,
            "authors": json.dumps(authors or [], ensure_ascii=False),
            "abstract": abstract,
            "publication_date": publication_date,
            "source": source,
            "source_id": source_id,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "url": url,
            "pdf_url": pdf_url,
            "journal_name": journal_name,
            "citation_count": citation_count,
            "year": year,
        }
