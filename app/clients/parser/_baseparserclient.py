from abc import ABC, abstractmethod
import importlib
from typing import List, Type

from app.schemas.core.configuration import ParserType
from app.schemas.core.documents import ParserParams
from app.schemas.parse import ParsedDocument


class BaseParserClient(ABC):
    SUPPORTED_FORMATS = []

    @staticmethod
    def import_module(type: ParserType) -> "Type[BaseParserClient]":
        """
        Static method to import a subclass of BaseParserClient.

        Args:
            type(str): The type of parser client to import.

        Returns:
            Type[BaseParserClient]: The subclass of BaseParserClient.
        """
        module = importlib.import_module(f"app.clients.parser._{type.value}parserclient")
        return getattr(module, f"{type.capitalize()}ParserClient")

    def convert_page_range(self, page_range: str, page_count: int) -> List[int]:
        if not page_range:
            return [i for i in range(page_count)]

        page_ranges = page_range.split(",")
        pages = []
        for page_range in page_ranges:
            page_range = page_range.split("-")
            if len(page_range) == 1:
                pages.append(int(page_range[0]))
            else:
                for i in range(int(page_range[0]), int(page_range[1]) + 1):
                    pages.append(i)

        pages = list(set(pages))

        return pages

    @abstractmethod
    def parse(self, params: ParserParams) -> ParsedDocument:
        pass
