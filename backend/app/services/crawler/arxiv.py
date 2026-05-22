import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import httpx

from app.services.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"


class ArxivCrawler(BaseCrawler):
    name = "arxiv"
    base_url = ARXIV_API_URL

    async def search(self, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        # Quote multi-word keywords for exact phrase search — arXiv treats spaces as OR otherwise
        query = f'all:"{keyword}"' if " " in keyword else f"all:{keyword}"
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        # arXiv requires a delay between requests to avoid 429
        await asyncio.sleep(3)
        resp = await self._request(self.base_url, params=params)
        return self._parse_response(resp.text)

    async def _request(self, url: str, params: dict | None = None) -> httpx.Response:
        headers = {"User-Agent": "PaperCrawler/0.1 (mailto:user@example.com)"}
        async with self.semaphore:
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", "30")
                    wait = int(retry_after) if retry_after.isdigit() else 30
                    logger.warning("arXiv rate limited, waiting %ds", wait)
                    await asyncio.sleep(wait)
                    resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp

    def _parse_response(self, xml_text: str) -> list[dict[str, Any]]:
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(xml_text)
        papers = []
        for entry in root.findall("atom:entry", ns):
            try:
                title = self._get_text(entry, "atom:title", ns)
                raw_authors = [a.text or "" for a in entry.findall("atom:author/atom:name", ns)]
                abstract = self._get_text(entry, "atom:summary", ns)
                arxiv_id = self._get_text(entry, "atom:id", ns)
                if arxiv_id:
                    arxiv_id = arxiv_id.replace("http://arxiv.org/abs/", "").strip()
                published = self._get_text(entry, "atom:published", ns)
                pub_date = None
                year = None
                if published:
                    try:
                        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        pub_date = dt.strftime("%Y-%m-%d")
                        year = dt.year
                    except ValueError:
                        pass

                pdf_url = None
                for link in entry.findall("atom:link", ns):
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href")
                        break

                categories = [c.get("term", "") for c in entry.findall("atom:category", ns)]

                papers.append(
                    self._to_paper_data(
                        title=title.strip() if title else "",
                        authors=raw_authors,
                        abstract=abstract.strip() if abstract else None,
                        publication_date=pub_date,
                        source="arxiv",
                        source_id=arxiv_id,
                        arxiv_id=arxiv_id,
                        url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
                        pdf_url=pdf_url,
                        journal_name=categories[0] if categories else None,
                        year=year,
                    )
                )
            except Exception as e:
                logger.warning("Failed to parse arXiv entry: %s", e)
                continue
        return papers

    def _get_text(self, element: ET.Element, tag: str, ns: dict) -> str | None:
        child = element.find(tag, ns)
        return child.text if child is not None else None
