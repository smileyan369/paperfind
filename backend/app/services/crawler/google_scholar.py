import asyncio
import logging
import re
from typing import Any

import httpx

from app.services.crawler.base import BaseCrawler
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

SCHOLAR_MIRRORS = [
    "https://scholar.google.com/scholar",
    "https://scholar.google.com.hk/scholar",
    "https://scholar.google.com.tw/scholar",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


class GoogleScholarCrawler(BaseCrawler):
    """Google Scholar crawler — fragile, may trigger CAPTCHA. Use with caution."""

    name = "google_scholar"
    base_url = SCHOLAR_MIRRORS[0]

    def __init__(self, semaphore: asyncio.Semaphore | None = None):
        # Force single-concurrency for Google Scholar
        super().__init__(semaphore or asyncio.Semaphore(1))
        self._agent_idx = 0
        self._last_request = 0.0

    async def _wait_rate_limit(self):
        """Enforce delay between requests to avoid CAPTCHA."""
        import time

        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < 15:
            delay = 15 - elapsed + 3
            logger.info("Google Scholar rate limit: waiting %.0fs", delay)
            await asyncio.sleep(delay)
        self._last_request = time.monotonic()

    def _next_ua(self) -> str:
        ua = USER_AGENTS[self._agent_idx % len(USER_AGENTS)]
        self._agent_idx += 1
        return ua

    @async_retry(max_retries=2, base_delay=30.0, exceptions=(httpx.HTTPError, ConnectionError))
    async def search(self, keyword: str, max_results: int = 100) -> list[dict[str, Any]]:
        all_papers: list[dict[str, Any]] = []
        start = 0
        per_page = 10  # Google Scholar shows 10 results per page

        while len(all_papers) < max_results:
            await self._wait_rate_limit()

            async with self.semaphore:
                async with httpx.AsyncClient(
                    timeout=30.0,
                    follow_redirects=True,
                    headers={
                        "User-Agent": self._next_ua(),
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                        "Accept-Encoding": "gzip, deflate, br",
                    },
                ) as client:
                    resp = await client.get(
                        self.base_url,
                        params={
                            "q": keyword,
                            "hl": "en",
                            "lr": "lang_en",
                            "num": per_page,
                            "start": start,
                        },
                    )
                    resp.raise_for_status()

            page_papers = self._parse_response(resp.text, max_results - len(all_papers))
            if not page_papers:
                break
            all_papers.extend(page_papers)
            start += per_page

            if len(page_papers) < per_page:
                break

        return all_papers

    def _parse_response(self, html: str, max_results: int) -> list[dict[str, Any]]:
        if self._is_captcha(html):
            logger.warning("Google Scholar CAPTCHA detected, returning empty")
            return []

        papers = []

        # Remove <style> blocks to avoid matching CSS class names
        clean = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

        # Results are in: <div class="gs_r gs_or gs_scl" data-cid="..." ...>
        # Find each result block start, then extract until next result or end marker
        block_starts = list(re.finditer(
            r'<div class="gs_r gs_or gs_scl" data-cid="([^"]*)"',
            clean,
        ))

        if not block_starts:
            logger.debug("No gs_r gs_or gs_scl blocks found")
            return []

        for i, m in enumerate(block_starts):
            if len(papers) >= max_results:
                break
            cid = m.group(1)
            start = m.start()
            # End is next result block start, or the "no results" end marker
            if i + 1 < len(block_starts):
                end = block_starts[i + 1].start()
            else:
                # Find the end marker: <div id="gs_res_em" or similar
                end_marker = re.search(r'<div[^>]*id="gs_res_ccl_bot"', clean[start:])
                if end_marker:
                    end = start + end_marker.start()
                else:
                    end = start + 30000  # fallback

            block = clean[start:end]
            try:
                paper = self._parse_block(block, cid)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.debug("Failed to parse GS block: %s", e)
                continue

        return papers

    def _parse_simple(self, html: str, max_results: int) -> list[dict[str, Any]]:
        """Fallback parser — directly extract per-element."""
        papers = []

        for m in re.finditer(
            r'<h3[^>]*class="[^"]*gs_rt[^"]*"[^>]*>(.*?)</h3>',
            html,
            re.DOTALL,
        ):
            if len(papers) >= max_results:
                break

            title_html = m.group(1)
            title = self._clean_html(title_html)
            if not title or title.startswith("[CITATION]") or title.startswith("[BOOK]"):
                continue

            # Try to find surrounding context
            ctx_start = max(0, m.start() - 2000)
            ctx_end = min(len(html), m.end() + 5000)
            ctx = html[ctx_start:ctx_end]

            authors_str, year = self._extract_authors_and_year(ctx)
            authors = self._parse_authors(authors_str)
            abstract = self._extract_snippet(ctx)
            url = self._extract_url_from_h3(title_html)
            citations = self._extract_citations(ctx)
            journal = self._extract_journal(authors_str)
            doi = self._extract_doi(ctx)

            papers.append(
                self._to_paper_data(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    publication_date=None,
                    source="google_scholar",
                    source_id="",
                    doi=doi,
                    url=url,
                    journal_name=journal,
                    citation_count=citations,
                    year=year,
                )
            )

        return papers

    def _parse_block(self, block: str, cid: str) -> dict[str, Any] | None:
        title = self._extract_title(block)
        if not title:
            return None

        authors_str, year = self._extract_authors_and_year(block)
        authors = self._parse_authors(authors_str)
        abstract = self._extract_snippet(block)
        url = self._extract_url(block)
        citations = self._extract_citations(block)
        journal = self._extract_journal(authors_str)

        # Try to find DOI in the snippet or URL
        doi = self._extract_doi(block)

        return self._to_paper_data(
            title=title,
            authors=authors,
            abstract=abstract,
            publication_date=None,
            source="google_scholar",
            source_id=cid,
            doi=doi,
            url=url,
            journal_name=journal,
            citation_count=citations,
            year=year,
        )

    def _extract_title(self, block: str) -> str | None:
        # Look for h3.gs_rt content
        m = re.search(r'<h3[^>]*class="[^"]*gs_rt[^"]*"[^>]*>\s*<a[^>]*>(.*?)</a>', block, re.DOTALL)
        if m:
            return self._clean_html(m.group(1))
        # Try without link
        m = re.search(r'<h3[^>]*class="[^"]*gs_rt[^"]*"[^>]*>(.*?)</h3>', block, re.DOTALL)
        if m:
            text = self._clean_html(m.group(1))
            if text and not text.startswith("[CITATION]") and not text.startswith("[BOOK]"):
                return text
        return None

    def _extract_authors_and_year(self, block: str) -> tuple[str, int | None]:
        m = re.search(r'<div[^>]*class="[^"]*gs_a[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL)
        if not m:
            return "", None

        text = self._clean_html(m.group(1))
        year = None
        # Extract year: look for 19xx or 20xx
        year_m = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        if year_m:
            try:
                year = int(year_m.group(1))
            except ValueError:
                pass

        # Remove the dash-separated parts after first dash (typically journal info)
        # The authors are everything before the first " - "
        parts = text.split(" - ")
        authors_str = parts[0] if parts else text

        return authors_str, year

    def _parse_authors(self, authors_str: str) -> list[str]:
        if not authors_str:
            return []
        # Authors are typically separated by ", "
        # Remove any trailing year
        authors_str = re.sub(r'\s+\d{4}\s*$', '', authors_str)
        names = [a.strip() for a in authors_str.split(",") if a.strip()]
        # Filter out common non-author suffixes
        names = [n for n in names if len(n) > 1 and not re.match(r'^(et al\.?|\.\.\.)$', n, re.IGNORECASE)]
        return names

    def _extract_snippet(self, block: str) -> str | None:
        m = re.search(r'<div[^>]*class="[^"]*gs_rs[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL)
        if m:
            text = self._clean_html(m.group(1))
            return text if text else None
        return None

    def _extract_url(self, block: str) -> str | None:
        m = re.search(r'<h3[^>]*class="[^"]*gs_rt[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"', block)
        if m:
            return m.group(1)
        return None

    def _extract_url_from_h3(self, title_html: str) -> str | None:
        m = re.search(r'<a[^>]*href="([^"]*)"', title_html)
        if m:
            return m.group(1)
        return None

    def _extract_citations(self, block: str) -> int:
        m = re.search(r'Cited by (\d+)', block)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return 0

    def _extract_journal(self, authors_str: str) -> str | None:
        # Journal is often after the first dash in gs_a text
        parts = authors_str.split(" - ")
        if len(parts) >= 2:
            candidate = parts[-1].strip()
            # Filter out things that aren't journal names
            if candidate and not re.match(r'^\d{4}$', candidate) and len(candidate) > 2:
                return candidate
        return None

    def _extract_doi(self, block: str) -> str | None:
        m = re.search(r'doi:\s*(10\.\d{4,}/[^\s<"]+)', block, re.IGNORECASE)
        if m:
            return m.group(1)
        # Try in URLs
        m = re.search(r'doi\.org/(10\.\d{4,}/[^\s<"&]+)', block)
        if m:
            return m.group(1)
        return None

    def _is_captcha(self, html: str) -> bool:
        captcha_markers = [
            "g-recaptcha",
            "Sorry, we can't verify",
            "unusual traffic",
            "CAPTCHA",
            "robot checking",
            "verify you're not a robot",
        ]
        lower = html.lower()
        return any(m.lower() in lower for m in captcha_markers)

    @staticmethod
    def _clean_html(text: str) -> str:
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode common entities
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&apos;", "'")
        text = re.sub(r'&[a-z]+;', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
