from typing import Any, Dict, List, Literal

from app.schemas import BaseModel


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    id: int | str
    metadata: Dict[str, Any]
    content: str


class Chunks(BaseModel):
    object: Literal["list"] = "list"
    data: List[Chunk]
