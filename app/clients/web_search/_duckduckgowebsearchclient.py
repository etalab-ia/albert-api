import logging
import traceback
from typing import List

import httpx

from app.clients.web_search._basewebsearchclient import BaseWebSearchClient

logger = logging.getLogger(__name__)


class DuckduckgoWebSearchClient(BaseWebSearchClient):
    URL = "https://api.duckduckgo.com/"
    DEFAULT_TIMEOUT = 5
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, *args, **kwargs) -> None:
        self.headers = {"User-Agent": self.USER_AGENT}

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
            logger.error(msg="DuckDuckGo API unreachable.")
            logger.debug(msg=traceback.format_exc())
            results = []

        return [result["FirstURL"].lower() for result in results]
