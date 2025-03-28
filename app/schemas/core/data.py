from typing import Dict, Any, List, Optional

from pydantic import BaseModel


class JsonFileDocument(BaseModel):
    title: Optional[str] = None
    text: str
    metadata: Dict[str, str] = {}


class JsonFile(BaseModel):
    documents: List[JsonFileDocument]


class ParserOutput(BaseModel):
    contents: list[str]
    metadata: Dict[str, Any] = {}
