from typing import Dict, Any

from pydantic import BaseModel


class Collection(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    model: str
    type: str
    created_at: int


class ParserOutput(BaseModel):
    contents: list[str]
    metadata: Dict[str, Any] = {}
