from abc import ABC, abstractmethod
from typing import List


class InternetClient(ABC):
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
