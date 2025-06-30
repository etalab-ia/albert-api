from abc import ABC, abstractmethod
import importlib
from typing import List, Type

from app.schemas.core.documents import ParserParams
from app.schemas.core.settings import ParserType
from app.schemas.parse import ParsedDocument


class BaseParserClient(ABC):
    SUPPORTED_FORMATS = []

    @staticmethod
    def import_module(parser_type: ParserType) -> "Type[BaseParserClient]":
        """
        Import the module for the given parser type.
        """
        module = importlib.import_module(f"app.clients.parser._{parser_type.value}parserclient")
        return getattr(module, f"{parser_type.capitalize()}ParserClient")

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
    def parse(self, **params: ParserParams) -> ParsedDocument:
        pass
