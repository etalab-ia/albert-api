from typing import Any, Dict, List, Literal

from pydantic import BaseModel


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    id: int
    metadata: Dict[str, Any]
    content: str


class Chunks(BaseModel):
    object: Literal["list"] = "list"
    data: List[Chunk]
