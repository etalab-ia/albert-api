import logging
from typing import List

import httpx

from app.clients.web_search._basewebsearchclient import BaseWebSearchClient

logger = logging.getLogger(__name__)


class DuckduckgoWebSearchClient(BaseWebSearchClient):
    URL = "https://api.duckduckgo.com/"
    DEFAULT_TIMEOUT = 5

    def __init__(self, user_agent: str, *args, **kwargs) -> None:
        self.headers = {"User-Agent": user_agent}

    async def search(self, query: str, n: int = 3) -> List[str]:
        params = {
            "q": query,
            "format": "json",
            "kl": "fr-fr",
            "safe": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                response = await client.get(url=self.URL, headers=self.headers, params=params, follow_redirects=True)
                results = response.json().get("Results", [])[:n]
        except Exception:
            logger.exception(msg="DuckDuckGo API unreachable.")
            results = []

        return [result["FirstURL"].lower() for result in results]
