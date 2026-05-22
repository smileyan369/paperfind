import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import httpx

from app.services.crawler.base import BaseCrawler
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

DBLP_SEARCH_URL = "https://dblp.org/search/publ/api"


class DBLPCrawler(BaseCrawler):
    name = "dblp"
    base_url = DBLP_SEARCH_URL

    @async_retry(max_retries=3, base_delay=2.0, exceptions=(httpx.HTTPError, ConnectionError))
    async def search(self, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "q": keyword,
            "h": max_results,
            "format": "xml",
        }
        resp = await self._request(self.base_url, params=params)
        return self._parse_response(resp.text)

    def _parse_response(self, xml_text: str) -> list[dict[str, Any]]:
        root = ET.fromstring(xml_text)
        hits = root.find("hits")
        if hits is None:
            return []

        papers = []
        for hit in hits.findall("hit"):
            try:
                info = hit.find("info")
                if info is None:
                    continue

                title_el = info.find("title")
                title = title_el.text if title_el is not None else ""

                raw_authors = []
                authors_el = info.find("authors")
                if authors_el is not None:
                    for a in authors_el.findall("author"):
                        if a.text:
                            raw_authors.append(a.text)

                year_el = info.find("year")
                year = None
                if year_el is not None and year_el.text:
                    try:
                        year = int(year_el.text)
                    except ValueError:
                        pass

                doi = None
                doi_el = info.find("doi")
                if doi_el is not None and doi_el.text:
                    doi = doi_el.text

                url_el = info.find("url")
                paper_url = url_el.text if url_el is not None else None

                venue_el = info.find("venue")
                journal_name = venue_el.text if venue_el is not None else None

                papers.append(
                    self._to_paper_data(
                        title=title.strip() if title else "",
                        authors=raw_authors,
                        abstract=None,
                        publication_date=None,
                        source="dblp",
                        source_id=str(hit.get("id", "")),
                        doi=doi,
                        url=paper_url,
                        journal_name=journal_name,
                        year=year,
                    )
                )
            except Exception as e:
                logger.warning("Failed to parse DBLP hit: %s", e)
                continue
        return papers
