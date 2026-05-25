import logging
import re
from datetime import date
from typing import Any

from app.services.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
TAG_RE = re.compile(r"<[^>]+>")


class CrossrefCrawler(BaseCrawler):
    name = "crossref"
    base_url = CROSSREF_WORKS_URL

    async def search(self, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "query": keyword,
            "rows": min(max_results, 100),
            "sort": "published",
            "order": "desc",
        }
        resp = await self._request(self.base_url, params=params)
        data = resp.json()

        papers = []
        for item in data.get("message", {}).get("items", []):
            try:
                paper = self._parse_paper(item)
                if paper["title"]:
                    papers.append(paper)
            except Exception as e:
                logger.warning("Failed to parse Crossref work: %s", e)
        return papers

    def _parse_paper(self, item: dict[str, Any]) -> dict[str, Any]:
        title = self._first_text(item.get("title"))
        authors = []
        for author in item.get("author", []) or []:
            name = " ".join(
                part for part in [author.get("given"), author.get("family")]
                if part
            ).strip()
            if name:
                authors.append(name)

        pub_date = self._published_date(item)
        year = None
        if pub_date:
            try:
                year = int(pub_date[:4])
            except ValueError:
                year = None

        doi = item.get("DOI")
        abstract = item.get("abstract")
        if abstract:
            abstract = TAG_RE.sub(" ", abstract)
            abstract = " ".join(abstract.split())

        return self._to_paper_data(
            title=title,
            authors=authors,
            abstract=abstract,
            publication_date=pub_date,
            source="crossref",
            source_id=doi or item.get("URL"),
            doi=doi,
            url=item.get("URL"),
            journal_name=self._first_text(item.get("container-title")),
            citation_count=item.get("is-referenced-by-count", 0) or 0,
            year=year,
        )

    def _first_text(self, value: Any) -> str:
        if isinstance(value, list) and value:
            return str(value[0] or "").strip()
        return str(value or "").strip()

    def _published_date(self, item: dict[str, Any]) -> str | None:
        for key in ("published-print", "published-online", "published"):
            parts = (item.get(key) or {}).get("date-parts") or []
            if not parts or not parts[0]:
                continue
            numbers = parts[0]
            try:
                year = int(numbers[0])
                month = int(numbers[1]) if len(numbers) > 1 else 1
                day = int(numbers[2]) if len(numbers) > 2 else 1
                return date(year, month, day).isoformat()
            except (TypeError, ValueError):
                continue
        return None
