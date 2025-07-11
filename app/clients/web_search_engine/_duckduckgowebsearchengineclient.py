import logging
from typing import Dict, List, Optional

import httpx

from app.clients.web_search_engine._basewebsearchengineclient import BaseWebSearchEngineClient

logger = logging.getLogger(__name__)


class DuckduckgoWebSearchEngineClient(BaseWebSearchEngineClient):
    URL = "https://api.duckduckgo.com/"

    def __init__(self, headers: Dict[str, str], timeout: int, url: Optional[str] = None, *args, **kwargs) -> None:
        self.url = url or self.URL
        self.headers = headers
        self.timeout = timeout
        self.additional_params = kwargs

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
