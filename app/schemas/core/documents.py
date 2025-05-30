from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FileType(str, Enum):
    PDF = "application/pdf"
    HTML = "text/html"
    JSON = "application/json"
    MD = "text/markdown"
    TXT = "text/plain"


class JsonFileDocument(BaseModel):
    title: Optional[str] = None
    text: str
    metadata: Dict[str, Any] = {}


class JsonFile(BaseModel):
    documents: List[JsonFileDocument]


class ParserOutput(BaseModel):
    contents: list[str]
    metadata: Dict[str, Any] = {}
