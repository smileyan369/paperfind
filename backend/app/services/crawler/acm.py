import logging
from typing import Any

from app.config import settings
from app.services.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)


class ACMLCrawler(BaseCrawler):
    name = "acm"
    base_url = "https://dl.acm.org/action/doSearch"
    is_supported = False

    async def search(self, keyword: str, max_results: int = 50) -> list[dict[str, Any]]:
        if not settings.acm_institution_cookie:
            logger.info("ACM cookie not configured, skipping")
            return []
        # TODO: Implement ACM Digital Library API when cookie is provided
        logger.warning("ACM crawler not fully implemented yet")
        return []
