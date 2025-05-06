import logging
import traceback
from typing import List

import httpx

from app.clients.web_search._basewebsearchclient import BaseWebSearchClient

logger = logging.getLogger(__name__)


class BraveWebSearchClient(BaseWebSearchClient):
    URL = "https://api.search.brave.com/res/v1/web/search"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    DEFAULT_TIMEOUT = 5

    def __init__(self, api_key: str, *args, **kwargs) -> None:
        self.api_key = api_key
        self.headers = {"Accept": "application/json", "X-Subscription-Token": self.api_key, "User-Agent": self.USER_AGENT}

    async def search(self, query: str, n: int = 3) -> List[str]:
        params = {"q": query, "count": n, "country": "fr", "safesearch": "strict"}

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                response = await client.get(url=self.URL, headers=self.headers, params=params)
                results = response.json().get("web", {}).get("results", [])
        except Exception:
            logger.error(msg="Brave Search API unreachable.")
            logger.debug(msg=traceback.format_exc())
            results = []

        return [result["url"].lower() for result in results]
