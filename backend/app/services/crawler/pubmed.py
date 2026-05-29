import logging
import xml.etree.ElementTree as ET
from typing import Any

from app.services.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class PubMedCrawler(BaseCrawler):
    name = "pubmed"
    base_url = PUBMED_SEARCH_URL

    async def search(self, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        search_resp = await self._request(
            PUBMED_SEARCH_URL,
            params={
                "db": "pubmed",
                "term": keyword,
                "retmax": min(max_results, 100),
                "retmode": "json",
                "sort": "pub date",
            },
        )
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        fetch_resp = await self._request(
            PUBMED_FETCH_URL,
            params={
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml",
            },
        )
        return self._parse_articles(fetch_resp.text)

    def _parse_articles(self, xml_text: str) -> list[dict[str, Any]]:
        root = ET.fromstring(xml_text)
        papers = []
        for article in root.findall(".//PubmedArticle"):
            try:
                paper = self._parse_article(article)
                if paper["title"]:
                    papers.append(paper)
            except Exception as e:
                logger.warning("Failed to parse PubMed article: %s", e)
        return papers

    def _parse_article(self, article: ET.Element) -> dict[str, Any]:
        pmid = self._text(article.find(".//PMID"))
        title = " ".join(self._text(article.find(".//ArticleTitle")).split())
        abstract_parts = []
        for node in article.findall(".//Abstract/AbstractText"):
            text = " ".join("".join(node.itertext()).split())
            if text:
                label = node.get("Label")
                abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = "\n".join(abstract_parts) or None

        authors = []
        for author in article.findall(".//AuthorList/Author"):
            last = self._text(author.find("LastName"))
            fore = self._text(author.find("ForeName"))
            collective = self._text(author.find("CollectiveName"))
            name = " ".join(part for part in [fore, last] if part).strip() or collective
            if name:
                authors.append(name)

        journal = self._text(article.find(".//Journal/Title"))
        pub_date, year = self._publication_date(article)
        doi = None
        for article_id in article.findall(".//ArticleIdList/ArticleId"):
            if article_id.get("IdType") == "doi":
                doi = self._text(article_id)
                break

        return self._to_paper_data(
            title=title,
            authors=authors,
            abstract=abstract,
            publication_date=pub_date,
            source="pubmed",
            source_id=pmid,
            doi=doi,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            journal_name=journal,
            year=year,
        )

    def _publication_date(self, article: ET.Element) -> tuple[str | None, int | None]:
        pub_date = article.find(".//JournalIssue/PubDate")
        if pub_date is None:
            return None, None
        year_text = self._text(pub_date.find("Year"))
        month_text = self._text(pub_date.find("Month")) or "1"
        day_text = self._text(pub_date.find("Day")) or "1"
        try:
            year = int(year_text)
        except ValueError:
            return None, None
        month = self._month_to_number(month_text)
        try:
            day = max(1, min(31, int(day_text)))
        except ValueError:
            day = 1
        return f"{year:04d}-{month:02d}-{day:02d}", year

    def _month_to_number(self, value: str) -> int:
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        try:
            return max(1, min(12, int(value)))
        except ValueError:
            return months.get(value[:3].lower(), 1)

    def _text(self, node: ET.Element | None) -> str:
        if node is None or node.text is None:
            return ""
        return node.text.strip()
