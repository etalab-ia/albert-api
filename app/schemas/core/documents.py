from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import UploadFile
from pydantic import BaseModel

from app.schemas.parse import Languages, ParsedDocumentOutputFormat


class ParserParams(BaseModel):
    file: UploadFile
    output_format: Optional[ParsedDocumentOutputFormat] = None
    force_ocr: bool = False
    languages: Optional[Languages] = None
    page_range: Optional[str] = None
    paginate_output: bool = False
    use_llm: bool = False


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
