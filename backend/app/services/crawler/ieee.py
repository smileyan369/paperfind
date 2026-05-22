import logging
from typing import Any

from app.config import settings
from app.services.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)


class IEEECrawler(BaseCrawler):
    name = "ieee"
    base_url = "https://ieeexplore.ieee.org/rest/search"
    is_supported = False

    async def search(self, keyword: str, max_results: int = 50) -> list[dict[str, Any]]:
        if not settings.ieee_institution_cookie:
            logger.info("IEEE cookie not configured, skipping")
            return []
        # TODO: Implement IEEE Xplore API when cookie is provided
        logger.warning("IEEE crawler not fully implemented yet")
        return []
