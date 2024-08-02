from typing import Literal, List
from uuid import UUID

from pydantic import BaseModel


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    collection: str
    id: str
    metadata: dict
    content: str


class ChunkResponse(BaseModel):
    object: Literal["list"] = "list"
    data: List[Chunk]


class ChunkRequest(BaseModel):
    ids: List[str]
