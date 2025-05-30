from abc import ABC, abstractmethod
import importlib
from typing import Optional, Type

from fastapi import UploadFile

from app.schemas.core.settings import ParserType
from app.schemas.parse import Languages, ParsedDocument, ParsedDocumentOutputFormat


class BaseParserClient(ABC):
    SUPPORTED_FORMATS = []

    @staticmethod
    def import_module(type: ParserType) -> "Type[BaseParserClient]":
        """
        Import the module for the given parser type.
        """
        module = importlib.import_module(f"app.clients.parser._{type.value}parserclient")
        return getattr(module, f"{type.capitalize()}ParserClient")

    @abstractmethod
    def parse(
        self,
        file: UploadFile,
        output_format: Optional[ParsedDocumentOutputFormat] = None,
        force_ocr: bool = False,
        languages: Optional[Languages] = None,
        page_range: Optional[str] = None,
        paginate_output: Optional[bool] = None,
        use_llm: Optional[bool] = None,
    ) -> ParsedDocument:
        pass
