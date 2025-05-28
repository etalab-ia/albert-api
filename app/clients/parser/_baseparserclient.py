from abc import ABC
from typing import Optional

from fastapi import UploadFile

from app.schemas.documents import Languages, ParsedDocument, ParsedDocumentOutputFormat


class BaseParserClient(ABC):
    SUPPORTED_FORMAT = []

    def __init__(self, api_url: str, api_key: str, timeout: int = 120):
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout

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
