import logging
from typing import List

import httpx

from app.clients.web_search._basewebsearchclient import BaseWebSearchClient

logger = logging.getLogger(__name__)


class DuckduckgoWebSearchClient(BaseWebSearchClient):
    URL = "https://api.duckduckgo.com/"
    DEFAULT_TIMEOUT = 5

    def __init__(self, timeout: int, *args, **kwargs) -> None:
        self.timeout = timeout
        self.additional_params = kwargs
        self.headers = {
            "Accept": "application/json",
        }

    async def search(self, query: str, k: int = 3) -> List[str]:
        params = {"q": query, "format": "json", "safe": 1} | self.additional_params
        results = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url=self.URL, headers=self.headers, params=params, follow_redirects=True)
                results = response.json().get("Results", [])[:k]
        except Exception:
            logger.exception(msg="DuckDuckGo API unreachable.")

        return [result["FirstURL"].lower() for result in results]
