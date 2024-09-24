from typing import Dict, List, Literal, Optional

from pydantic import BaseModel
from fastapi import Form


class File(BaseModel):
    object: Literal["file"] = "file"
    id: str
    bytes: int
    name: str
    chunks: Optional[list] = []
    created_at: int


class Files(BaseModel):
    object: Literal["list"] = "list"
    data: List[File]


class FilesRequest(BaseModel):
    collection: str = Form(...)
    embeddings_model: str = Form(...)
    chunk_size: int = Form(512)
    chunk_overlap: int = Form(0)
    chunk_min_size: Optional[int] = Form(None)


class Json(BaseModel):
    text: str
    metadata: Optional[Dict] = None


class JsonFile(BaseModel):
    documents: List[Json]
