import asyncio
import logging
from typing import Any

import httpx

from app.services.crawler.base import BaseCrawler
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"


class SemanticScholarCrawler(BaseCrawler):
    name = "semantic_scholar"
    base_url = SEMANTIC_SCHOLAR_API

    def __init__(self, api_key: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key

    @async_retry(max_retries=3, base_delay=2.0, exceptions=(httpx.HTTPError, ConnectionError))
    async def search(self, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        fields = (
            "title,authors,abstract,year,citationCount,externalIds,"
            "journal,publicationVenue,publicationDate,url"
        )
        papers = []
        offset = 0
        batch_size = min(max_results, 20)

        while offset < max_results:
            params: dict[str, str | int] = {
                "query": keyword,
                "limit": batch_size,
                "offset": offset,
                "fields": fields,
            }
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            async with self.semaphore:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(self.base_url, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()

            for item in data.get("data", []):
                try:
                    papers.append(self._parse_paper(item))
                except Exception as e:
                    logger.warning("Failed to parse Semantic Scholar paper: %s", e)

            if len(data.get("data", [])) < batch_size:
                break
            offset += batch_size
            await asyncio.sleep(1)

        return papers

    def _parse_paper(self, item: dict) -> dict[str, Any]:
        ext_ids = item.get("externalIds", {}) or {}
        journal = item.get("journal") or {}
        venue = item.get("publicationVenue") or {}
        journal_name = journal.get("name") or venue.get("name")

        authors = [a.get("name", "") for a in item.get("authors", [])]
        pub_date = item.get("publicationDate")
        doi = ext_ids.get("DOI")
        arxiv_id = ext_ids.get("ArXiv")

        return self._to_paper_data(
            title=item.get("title", ""),
            authors=authors,
            abstract=item.get("abstract"),
            publication_date=pub_date,
            source="semantic_scholar",
            source_id=item.get("paperId"),
            doi=doi,
            arxiv_id=arxiv_id,
            url=item.get("url"),
            journal_name=journal_name,
            citation_count=item.get("citationCount", 0) or 0,
            year=item.get("year"),
        )
