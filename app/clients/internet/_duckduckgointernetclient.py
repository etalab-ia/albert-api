from typing import List

from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException

from app.clients import InternetClient
from app.utils.logging import logger


class DuckDuckGoInternetClient(InternetClient):
    def __init__(self, *args, **kwargs) -> None:
        pass

    def get_result_urls(self, query: str, n: int = 3) -> List[str]:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(keywords=query, region="fr-fr", safesearch="On", max_results=n))
        except RatelimitException:
            logger.warning(msg="DuckDuckGo rate limit exceeded.")
            results = []

        return [result["href"].lower() for result in results]
