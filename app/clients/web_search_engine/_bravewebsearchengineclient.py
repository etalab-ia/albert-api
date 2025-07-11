import logging
from typing import Dict, List, Optional

import httpx

from app.clients.web_search_engine._basewebsearchengineclient import BaseWebSearchEngineClient

logger = logging.getLogger(__name__)


class BraveWebSearchEngineClient(BaseWebSearchEngineClient):
    URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, headers: Dict[str, str], timeout: int, url: Optional[str] = None, *args, **kwargs) -> None:
        self.url = url or self.URL
        self.headers = headers
        self.timeout = timeout
        self.additional_params = kwargs

    async def search(self, query: str, k: int) -> List[str]:
        params = {"q": query, "count": k} | self.additional_params
        results = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url=self.URL, headers=self.headers, params=params)
                results = response.json().get("web", {}).get("results", [])
        except Exception:
            logger.exception(msg="Brave Search API unreachable.")

        return [result["url"].lower() for result in results]
