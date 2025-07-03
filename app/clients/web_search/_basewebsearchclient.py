from abc import ABC, abstractmethod
import importlib
from typing import List, Type

from app.schemas.core.settings import WebSearchType


class BaseWebSearchClient(ABC):
    @staticmethod
    def import_module(websearch_type: WebSearchType) -> "Type[BaseWebSearchClient]":
        """
        Import the module for the given web search type.
        """
        module = importlib.import_module(f"app.clients.web_search._{websearch_type.value}websearchclient")
        return getattr(module, f"{websearch_type.capitalize()}WebSearchClient")

    @abstractmethod
    async def search(self, query: str, n: int = 3) -> List[str]:
        """
        Get the URLs of the search results for a given query.

        Args:
            query (str): The query to search for.
            n (int): The number of results to return.

        Returns:
            List[str]: The URLs of the search results.
        """
        pass
