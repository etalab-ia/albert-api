from typing import Literal, List

from pydantic import BaseModel


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    id: str
    metadata: dict
    content: str


class Chunks(BaseModel):
    object: Literal["list"] = "list"
    data: List[Chunk]


class ChunkRequest(BaseModel):
    chunks: List[str]
