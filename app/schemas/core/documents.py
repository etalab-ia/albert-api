from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import UploadFile
from pydantic import BaseModel

from app.schemas.parse import ParsedDocumentOutputFormat


class ParserParams(BaseModel):
    file: UploadFile
    output_format: Optional[ParsedDocumentOutputFormat] = None
    force_ocr: Optional[bool] = None
    page_range: str = ""
    paginate_output: Optional[bool] = None
    use_llm: Optional[bool] = None


class FileType(str, Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    MD = "md"
    TXT = "txt"


class JsonFileDocument(BaseModel):
    title: Optional[str] = None
    text: str
    metadata: Dict[str, Any] = {}


class JsonFile(BaseModel):
    documents: List[JsonFileDocument]
