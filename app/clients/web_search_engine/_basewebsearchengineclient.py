from abc import ABC, abstractmethod
import importlib
from typing import List, Type

from app.schemas.core.configuration import WebSearchEngineType


class BaseWebSearchEngineClient(ABC):
    @staticmethod
    def import_module(type: WebSearchEngineType) -> "Type[BaseWebSearchEngineClient]":
        """
        Static method to import a subclass of BaseWebSearchEngineClient.

        Args:
            type(str): The type of web search engine client to import.

        Returns:
            Type[BaseWebSearchEngineClient]: The subclass of BaseWebSearchEngineClient.
        """
        module = importlib.import_module(f"app.clients.web_search_engine._{type.value}websearchengineclient")

        return getattr(module, f"{type.capitalize()}WebSearchEngineClient")

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
