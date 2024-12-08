from typing import List

import requests

from app.clients import InternetClient
from app.utils.logging import logger


class BraveInternetClient(InternetClient):
    URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, *args, **kwargs) -> None:
        self.api_key = api_key
        self.headers = {"Accept": "application/json", "X-Subscription-Token": self.api_key}

    def get_result_urls(self, query: str, n: int = 3) -> List[str]:
        params = {"q": query, "count": n, "country": "fr", "safesearch": "strict"}

        try:
            response = requests.get(url=self.URL, headers=self.headers, params=params)
            results = response.json().get("web", {}).get("results", [])
        except Exception as e:
            logger.warning(msq=f"Brave Search API error: {str(e)}")
            results = []

        return [result["url"].lower() for result in results]
