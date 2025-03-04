from abc import ABC, abstractmethod
import importlib
from typing import List, Type

from app.schemas.core.settings import InternetType


class BaseInternetClient(ABC):
    @staticmethod
    def import_module(type: InternetType) -> "Type[BaseInternetClient]":
        """
        Import the module for the given internet type.
        """
        module = importlib.import_module(f"app.clients.internet._{type.value}internetclient")
        return getattr(module, f"{type.capitalize()}InternetClient")

    @abstractmethod
    def get_result_urls(self, query: str, n: int = 3) -> List[str]:
        """
        Get the URLs of the search results for a given query.

        Args:
            query (str): The query to search for.
            n (int): The number of results to return.

        Returns:
            List[str]: The URLs of the search results.
        """
        pass
