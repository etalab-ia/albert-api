import traceback
from typing import List

import httpx

from app.clients import InternetClient
from app.utils.logging import logger


class DuckDuckGoInternetClient(InternetClient):
    URL = "https://api.duckduckgo.com/"
    DEFAULT_TIMEOUT = 5

    def __init__(self, *args, **kwargs) -> None:
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def get_result_urls(self, query: str, n: int = 3) -> List[str]:
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
        except Exception as e:
            logger.error(msg="DuckDuckGo API unreachable.")
            logger.debug(msg=traceback.format_exc())
            results = []

        return [result["FirstURL"].lower() for result in results]
