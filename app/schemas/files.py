from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class File(BaseModel):
    object: Literal["file"] = "file"
    id: UUID
    bytes: int
    file_name: str
    chunks: Optional[list] = []
    created_at: int


class Files(BaseModel):
    object: Literal["list"] = "list"
    data: List[File]


class Upload(BaseModel):
    object: Literal["upload"] = "upload"
    id: UUID
    file_name: str
    status: Literal["success", "failed"] = "success"


class Uploads(BaseModel):
    object: Literal["list"] = "list"
    data: List[Upload]


class Json(BaseModel):
    text: str
    metadata: Optional[Dict] = None


class JsonFile(BaseModel):
    documents: List[Json]
