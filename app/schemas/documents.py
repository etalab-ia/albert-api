from enum import Enum
from typing import Any, List, Literal, Optional

from app.schemas import BaseModel
from app.utils.variables import AUDIO_SUPPORTED_LANGUAGES

LANGUAGES = {key.title(): value for key, value in AUDIO_SUPPORTED_LANGUAGES.items()}
LANGUAGES = list(LANGUAGES.keys()) + list(LANGUAGES.values())
LANGUAGES = {str(lang).upper(): str(lang) for lang in sorted(set(LANGUAGES))}

Languages = Enum("Language", LANGUAGES, type=str)


class Document(BaseModel):
    object: Literal["document"] = "document"
    id: int
    name: str
    collection_id: int
    created_at: int
    chunks: Optional[int] = None


class Documents(BaseModel):
    object: Literal["list"] = "list"
    data: List[Document]


class ParsedDocumentOutputFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class ParsedDocument(BaseModel):
    format: ParsedDocumentOutputFormat
    output: str
    images: dict[str, str]
    metadata: dict[str, Any]
    success: bool
