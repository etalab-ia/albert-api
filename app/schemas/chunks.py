from typing import List, Literal

from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    collection_id: str
    document_id: str
    document_name: str
    document_part: int
    internet_query: str | None = None

    class Config:
        extra = "allow"


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    id: str
    metadata: ChunkMetadata
    content: str


class Chunks(BaseModel):
    object: Literal["list"] = "list"
    data: List[Chunk]
