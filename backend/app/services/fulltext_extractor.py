"""
Full-text extraction with layered fallback: PDF → HTML → abstract → metadata.
"""

import asyncio
import io
import logging
import re
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# ---- PDF extraction ----

def _extract_pdf_text(pdf_bytes: bytes) -> str | None:
    """Extract text from PDF bytes using pymupdf (best quality)."""
    try:
        import fitz  # pymupdf
    except ImportError:
        logger.warning("pymupdf not installed, falling back to pypdf")
        return _extract_pdf_pypdf(pdf_bytes)

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        parts: list[str] = []
        for page in doc:
            text = page.get_text()
            if text:
                parts.append(text)
        doc.close()
        full = "\n\n".join(parts).strip()
        return full if len(full) > 100 else None
    except Exception as e:
        logger.warning("pymupdf extraction failed: %s, trying pypdf", e)
        return _extract_pdf_pypdf(pdf_bytes)


def _extract_pdf_pypdf(pdf_bytes: bytes) -> str | None:
    """Fallback PDF extraction with pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        full = "\n\n".join(parts).strip()
        return full if len(full) > 100 else None
    except Exception as e:
        logger.warning("pypdf extraction failed: %s", e)
        return None


# ---- HTML / webpage extraction ----

def _extract_html_text(html_bytes: bytes) -> str | None:
    """Extract main content from HTML using trafilatura, fallback to BeautifulSoup."""
    try:
        import trafilatura
    except ImportError:
        logger.warning("trafilatura not installed")
        return _extract_html_bs(html_bytes)

    try:
        text = trafilatura.extract(html_bytes, include_comments=False, include_tables=False)
        if text and len(text) > 200:
            return text.strip()
    except Exception as e:
        logger.warning("trafilatura extraction failed: %s", e)

    return _extract_html_bs(html_bytes)


def _extract_html_bs(html_bytes: bytes) -> str | None:
    """Fallback: BeautifulSoup body text extraction."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None
    try:
        soup = BeautifulSoup(html_bytes, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        body = soup.find("body")
        text = body.get_text(separator="\n") if body else soup.get_text(separator="\n")
        # Collapse whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip() if len(text) > 200 else None
    except Exception as e:
        logger.warning("BeautifulSoup extraction failed: %s", e)
        return None


# ---- Main service ----

class FulltextExtractor:
    """Try to get the best available text for a paper."""

    def __init__(self, timeout: float = 30.0, max_pdf_mb: int = 20):
        self.timeout = timeout
        self.max_pdf_bytes = max_pdf_mb * 1024 * 1024

    async def _download(self, url: str) -> bytes | None:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; PaperSearch/1.0; mailto:dev@example.com)"
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True, headers=headers
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                content = resp.read()
                if len(content) > self.max_pdf_bytes:
                    logger.warning("Download too large: %s (%d bytes)", url, len(content))
                    return None
                return content
        except Exception as e:
            logger.info("Download failed for %s: %s", url, e)
            return None

    async def get_best_available_text(self, paper) -> dict:
        """
        Returns {"source": str, "text": str, "source_chars": int, "error": str | None}
        Tries PDF → HTML → abstract → metadata in order.
        `paper` should have: pdf_url, url, abstract, title, authors, journal_name, year, keywords
        """
        # Tier 1: PDF full-text
        if getattr(paper, "pdf_url", None):
            pdf_bytes = await self._download(paper.pdf_url)
            if pdf_bytes:
                text = await asyncio.to_thread(_extract_pdf_text, pdf_bytes)
                if text:
                    logger.info("PDF extraction success for paper %d (%d chars)", paper.id, len(text))
                    return {"source": "pdf", "text": text, "source_chars": len(text), "error": None}
                logger.info("PDF text extraction yielded nothing for paper %d", paper.id)
            else:
                logger.info("PDF download failed for paper %d, trying next tier", paper.id)

        # Tier 2: HTML webpage
        if getattr(paper, "url", None):
            html_bytes = await self._download(paper.url)
            if html_bytes:
                text = await asyncio.to_thread(_extract_html_text, html_bytes)
                if text:
                    logger.info("HTML extraction success for paper %d (%d chars)", paper.id, len(text))
                    return {"source": "html", "text": text, "source_chars": len(text), "error": None}
                logger.info("HTML text extraction yielded nothing for paper %d", paper.id)
            else:
                logger.info("HTML download failed for paper %d, trying next tier", paper.id)

        # Tier 3: Abstract
        abstract = getattr(paper, "abstract", None)
        if abstract and len(abstract.strip()) > 20:
            logger.info("Using abstract for paper %d (%d chars)", paper.id, len(abstract))
            return {"source": "abstract", "text": abstract, "source_chars": len(abstract), "error": None}

        # Tier 4: Metadata only
        metadata = _build_metadata_text(paper)
        logger.info("Using metadata only for paper %d", paper.id)
        return {"source": "metadata", "text": metadata, "source_chars": len(metadata), "error": None}


def _build_metadata_text(paper) -> str:
    """Build a minimal text from metadata fields."""
    parts = []
    title = getattr(paper, "title", None)
    if title:
        parts.append(f"标题：{title}")

    authors = getattr(paper, "authors", "[]")
    try:
        import json
        author_list = json.loads(authors) if isinstance(authors, str) else authors
        if author_list:
            parts.append(f"作者：{', '.join(author_list[:10])}")
    except Exception:
        pass

    journal = getattr(paper, "journal_name", None)
    if journal:
        parts.append(f"期刊：{journal}")

    year = getattr(paper, "year", None) or getattr(paper, "publication_date", None)
    if year:
        year_str = str(year)[:4] if hasattr(year, "year") else str(year)
        parts.append(f"年份：{year_str}")

    keywords = getattr(paper, "keywords", [])
    if keywords:
        kw_texts = [kw.text if hasattr(kw, "text") else str(kw) for kw in keywords]
        if kw_texts:
            parts.append(f"关键词：{', '.join(kw_texts[:10])}")

    sourced = getattr(paper, "source", None)
    if sourced:
        parts.append(f"来源：{sourced}")

    doi = getattr(paper, "doi", None)
    if doi:
        parts.append(f"DOI：{doi}")

    return "\n".join(parts) if parts else "无可获取的论文内容"
