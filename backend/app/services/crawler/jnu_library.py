"""
暨南大学图书馆 发现系统爬虫 (覆盖 CNKI/知网、维普、万方等中文数据库)

通过图书馆的"四海搜索"发现系统检索期刊论文，结果包含 CNKI 等中文数据库内容。
不需要直接访问 CNKI（知网有 JS 验证），而是通过图书馆统一搜索间接获取。

搜索类型: type=3 (期刊论文) — 涵盖知网、维普、万方、Elsevier、Springer 等
"""

import asyncio
import logging
import re
from typing import Any

import httpx

from app.services.crawler.base import BaseCrawler
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

SEARCH_URL = "https://lib.jnu.edu.cn/asset/search"

# 搜索字段: T=题名, U=全部字段, K=主题词, A=作者, S=文摘
SEARCH_FIELD = "T"

# 期刊论文 type=3, 四海搜索 type=0
SEARCH_TYPE = "3"

# Browser-like headers to reduce bot detection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


class JNULibraryCrawler(BaseCrawler):
    """暨大图书馆发现系统爬虫 — 覆盖知网等中文数据库的期刊论文"""

    name = "jnu_library"
    base_url = SEARCH_URL

    def __init__(self, semaphore: asyncio.Semaphore | None = None):
        super().__init__(semaphore or asyncio.Semaphore(2))
        self._last_request = 0.0

    async def _wait_rate_limit(self):
        """Be gentle with the library server."""
        import time

        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < 5:
            await asyncio.sleep(5 - elapsed + 1)
        self._last_request = time.monotonic()

    @async_retry(max_retries=3, base_delay=2.0, exceptions=(httpx.HTTPError, ConnectionError))
    async def search(self, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        await self._wait_rate_limit()

        skey = f"{SEARCH_TYPE}_{SEARCH_FIELD}_{keyword}"
        key = f"{SEARCH_FIELD}={keyword.replace('(', '（').replace(')', '）')}"

        async with self.semaphore:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=HEADERS) as client:
                resp = await client.get(
                    self.base_url,
                    params={
                        "key": key,
                        "skey": skey,
                    },
                )
                resp.raise_for_status()

        # Detect CAPTCHA / robot verification page
        if self._is_blocked(resp.text):
            logger.warning("JNU Library returned CAPTCHA/verification page — IP may be rate-limited")
            return []

        papers = self._parse_search_results(resp.text, max_results)

        # Enrich with detail page data (limited to avoid overloading server)
        enriched = []
        for i, paper in enumerate(papers):
            if i < 5 and paper.get("url"):  # Only fetch first 5 details
                try:
                    await self._wait_rate_limit()
                    detail = await self._fetch_detail(paper["url"])
                    paper.update(detail)
                except Exception as e:
                    logger.debug("Failed to fetch detail for %s: %s", paper.get("title", "")[:40], e)
            enriched.append(paper)

        return enriched

    async def _fetch_detail(self, detail_url: str) -> dict[str, Any]:
        """Fetch paper detail page and extract metadata."""
        async with self.semaphore:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=HEADERS) as client:
                resp = await client.get(detail_url)
                resp.raise_for_status()
        if self._is_blocked(resp.text):
            return {}
        return self._parse_detail_page(resp.text)

    def _parse_search_results(self, html: str, max_results: int) -> list[dict[str, Any]]:
        """Parse the library search result page (DT/DD structure)."""
        papers = []

        # Find all DT elements (titles) and their following DD (metadata)
        # The results are in a DL structure
        dts = re.findall(r'<dt[^>]*>(.*?)</dt>', html, re.DOTALL)
        dds = re.findall(r'<dd[^>]*>(.*?)</dd>', html, re.DOTALL)

        # Skip the first few DT/DD pairs (they're filter/header, not results)
        # Results start after the filter section
        result_dts = []
        for dt in dts:
            # A result DT contains an <a> link to /asset/detail/
            if re.search(r'/asset/detail/', dt):
                result_dts.append(dt)

        for i, dt in enumerate(result_dts[:max_results]):
            try:
                title = self._clean(dt)
                link = ""
                link_m = re.search(r'href="([^"]*)"', dt)
                if link_m:
                    link = "https://lib.jnu.edu.cn" + link_m.group(1)

                if not title or len(title) < 3:
                    continue

                # Try to find matching DD
                meta = ""
                dd_idx = i
                # DDs for results start after the filter DDs; find by approximate index
                meta_dds = [d for d in dds if self._is_metadata_dd(d)]
                if i < len(meta_dds):
                    meta = self._clean(meta_dds[i])

                year, authors, journal, abstract, keywords, doi = self._parse_meta(meta)

                papers.append(
                    self._to_paper_data(
                        title=title,
                        authors=authors if authors else [],
                        abstract=abstract,
                        publication_date=None,
                        source="jnu_library",
                        source_id=link.split("/")[-1] if link else None,
                        doi=doi,
                        url=link,
                        journal_name=journal,
                        year=year,
                    )
                )
            except Exception as e:
                logger.debug("Failed to parse JNU search result: %s", e)
                continue

        return papers

    def _parse_detail_page(self, html: str) -> dict[str, Any]:
        """Extract metadata from a paper detail page."""
        result: dict[str, Any] = {}

        # Try to find metadata in various formats
        for label, key, patterns in [
            ("作者", "authors", [r'作者[：:]\s*([^<\n]{2,200})']),
            ("期刊", "journal", [r'刊名[：:]\s*([^<\n]{2,200})', r'期刊[：:]\s*([^<\n]{2,200})']),
            ("年份", "year", [r'(?:年份|出版年)[：:]\s*(\d{4})']),
            ("摘要", "abstract", [r'摘要[：:]\s*([^<\n]{10,2000})']),
            ("关键词", "keywords", [r'关键词[：:]\s*([^<\n]{2,500})']),
            ("DOI", "doi", [r'DOI[：:]\s*(10\.\d{4,}/[^\s<]{5,100})']),
        ]:
            for pattern in patterns:
                m = re.search(pattern, html)
                if m:
                    val = self._clean(m.group(1))
                    if val and len(val) > 1:
                        if key == "year":
                            try:
                                result[key] = int(val)
                            except ValueError:
                                pass
                        elif key == "authors":
                            result[key] = [a.strip() for a in val.replace("；", ";").replace("，", ",").split(";") if a.strip()]
                        else:
                            result[key] = val
                        break

        # Also try extracting from the page title
        title_m = re.search(r'<title[^>]*>(.*?)-[^-]*暨南大学图书馆</title>', html)
        if title_m:
            result["title_from_page"] = self._clean(title_m.group(1))

        return result

    def _parse_meta(self, meta: str) -> tuple[int | None, list[str] | None, str | None, str | None, str | None, str | None]:
        """Parse metadata from search result DD text."""
        year = None
        authors = None
        journal = None
        abstract = None
        keywords = None
        doi = None

        # Extract year — only accept reasonable publication years
        for year_m in re.finditer(r'(\d{4})', meta):
            try:
                y = int(year_m.group(1))
                if 1900 <= y <= 2030:
                    year = y
                    break
            except ValueError:
                pass

        # Extract authors
        author_m = re.search(r'作者[：:]\s*([^<\n]{2,200})', meta)
        if author_m:
            author_text = self._clean(author_m.group(1))
            authors = [a.strip() for a in author_text.replace("；", ";").split(";") if a.strip()]
            if len(authors) == 1:
                authors = [a.strip() for a in author_text.replace("，", ",").split(",") if a.strip()]

        # Extract DOI
        doi_m = re.search(r'(10\.\d{4,}/[^\s<>]{5,100})', meta)
        if doi_m:
            doi = doi_m.group(1)

        # If meta is long enough, it might contain an abstract
        if len(meta) > 100 and not authors:
            abstract = meta[:800]  # Take first portion as abstract

        # Keywords
        kw_m = re.search(r'关键词[：:]\s*([^<\n]{2,300})', meta)
        if kw_m:
            keywords = self._clean(kw_m.group(1))

        return year, authors, journal, abstract, keywords, doi

    @staticmethod
    def _clean(text: str) -> str:
        """Strip HTML tags and decode entities."""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&nbsp;", " ")
        text = re.sub(r'&#\d+;', '', text)
        text = re.sub(r'&[a-z]+;', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _is_blocked(html: str) -> bool:
        """Detect CAPTCHA / robot verification page."""
        markers = ["form-robot", "/Home/Robot", "请验证", "输入验证码", "访问出现异常"]
        return any(m in html for m in markers)

    @staticmethod
    def _is_metadata_dd(dd: str) -> bool:
        """Check if a DD element contains paper metadata (not UI buttons)."""
        # Filter out DDs that are clearly UI elements
        ui_markers = ["收藏", "导出", "引用", "class=\"save", "class=\"export", "class=\"cite"]
        return not any(m in dd for m in ui_markers)
