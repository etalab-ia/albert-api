from typing import List, Literal

from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    class Config:
        extra = "allow"


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    id: int
    metadata: ChunkMetadata
    content: str


class Chunks(BaseModel):
    object: Literal["list"] = "list"
    data: List[Chunk]
