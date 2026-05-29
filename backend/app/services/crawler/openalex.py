import logging
from typing import Any

from app.services.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


class OpenAlexCrawler(BaseCrawler):
    name = "openalex"
    base_url = OPENALEX_WORKS_URL

    async def search(self, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "search": keyword,
            "per-page": min(max_results, 100),
            "sort": "publication_date:desc",
        }
        resp = await self._request(self.base_url, params=params)
        data = resp.json()

        papers = []
        for item in data.get("results", []):
            try:
                paper = self._parse_work(item)
                if paper["title"]:
                    papers.append(paper)
            except Exception as e:
                logger.warning("Failed to parse OpenAlex work: %s", e)
        return papers

    def _parse_work(self, item: dict[str, Any]) -> dict[str, Any]:
        doi = item.get("doi")
        if isinstance(doi, str):
            doi = doi.replace("https://doi.org/", "")

        authors = []
        for authorship in item.get("authorships", []) or []:
            author = authorship.get("author") or {}
            name = author.get("display_name")
            if name:
                authors.append(name)

        abstract = self._abstract_from_index(item.get("abstract_inverted_index"))
        journal_name = None
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        journal_name = source.get("display_name")
        if not journal_name:
            host_venue = item.get("host_venue") or {}
            journal_name = host_venue.get("display_name")
        best_oa_location = item.get("best_oa_location") or {}
        landing_url = (
            best_oa_location.get("landing_page_url")
            or primary_location.get("landing_page_url")
            or item.get("doi")
            or item.get("id")
        )
        pdf_url = best_oa_location.get("pdf_url") or primary_location.get("pdf_url")

        return self._to_paper_data(
            title=item.get("display_name") or item.get("title") or "",
            authors=authors,
            abstract=abstract,
            publication_date=item.get("publication_date"),
            source="openalex",
            source_id=item.get("id"),
            doi=doi,
            url=landing_url,
            pdf_url=pdf_url,
            journal_name=journal_name,
            citation_count=item.get("cited_by_count", 0) or 0,
            year=item.get("publication_year"),
        )

    def _abstract_from_index(self, index: dict[str, list[int]] | None) -> str | None:
        if not index:
            return None
        words: list[tuple[int, str]] = []
        for word, positions in index.items():
            for position in positions:
                words.append((position, word))
        if not words:
            return None
        return " ".join(word for _, word in sorted(words))
