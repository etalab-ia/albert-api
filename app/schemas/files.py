from typing import Literal, List
from uuid import UUID

from pydantic import BaseModel


class File(BaseModel):
    object: Literal["file"]
    id: UUID
    bytes: int
    filename: str
    created_at: int


class FileResponse(BaseModel):
    object: Literal["list"]
    data: List[File]


class FileUpload(BaseModel):
    object: Literal["upload"]
    id: UUID
    filename: str
    status: Literal["success", "failed"]


class FileUploadResponse(BaseModel):
    object: Literal["list"]
    data: List[FileUpload]
