import logging
from typing import Any

from app.services.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)

EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class EuropePMCCrawler(BaseCrawler):
    name = "europe_pmc"
    base_url = EUROPE_PMC_SEARCH_URL

    async def search(self, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "query": keyword,
            "format": "json",
            "pageSize": min(max_results, 100),
            "sort": "FIRST_PDATE_D desc",
            "resultType": "core",
        }
        resp = await self._request(self.base_url, params=params)
        data = resp.json()

        papers: list[dict[str, Any]] = []
        for item in data.get("resultList", {}).get("result", []):
            try:
                paper = self._parse_result(item)
                if paper["title"]:
                    papers.append(paper)
            except Exception as e:
                logger.warning("Failed to parse Europe PMC result: %s", e)
        return papers

    def _parse_result(self, item: dict[str, Any]) -> dict[str, Any]:
        authors = []
        author_string = item.get("authorString")
        if author_string:
            authors = [a.strip() for a in author_string.rstrip(".").split(",") if a.strip()]

        doi = item.get("doi")
        pmid = item.get("pmid")
        pmcid = item.get("pmcid")
        pub_date = item.get("firstPublicationDate") or item.get("firstIndexDate")
        if pub_date:
            pub_date = str(pub_date)[:10]

        pdf_url = None
        if pmcid:
            pdf_url = f"https://europepmc.org/articles/{pmcid}?pdf=render"

        source_id = pmcid or pmid or doi
        return self._to_paper_data(
            title=item.get("title") or "",
            authors=authors,
            abstract=item.get("abstractText"),
            publication_date=pub_date,
            source="europe_pmc",
            source_id=source_id,
            doi=doi,
            url=f"https://europepmc.org/article/{item.get('source', 'MED')}/{source_id}" if source_id else None,
            pdf_url=pdf_url,
            journal_name=item.get("journalTitle"),
            citation_count=int(item.get("citedByCount") or 0),
            year=int(item["pubYear"]) if str(item.get("pubYear") or "").isdigit() else None,
        )
