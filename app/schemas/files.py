from typing import Dict, List, Literal, Optional

from fastapi import Form
from pydantic import BaseModel, Field

from app.utils.variables import CHUNKERS, DEFAULT_CHUNKER, SUPPORTED_FILE_TYPES


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


class ChunkerArgs(BaseModel):
    chunk_size: int = Form(512)
    chunk_overlap: int = Form(0)
    length_function: Literal[len] = len
    is_separator_regex: bool = False
    separators: List[str] = ["\n\n", "\n"]

    # additional arguments
    chunk_min_size: Optional[int] = Form(None)


class Chunker(BaseModel):
    name: Literal[*CHUNKERS] = DEFAULT_CHUNKER
    args: ChunkerArgs


class FilesRequest(BaseModel):
    collection: str = Form(...)
    embeddings_model: str = Form(...)
    chunker: Chunker
    file_type: Optional[Literal[*SUPPORTED_FILE_TYPES]] = None  # TODO: try with tuple(List)
    file_name: Optional[str] = Field(None, min_length=1)


class Json(BaseModel):
    text: str
    metadata: Optional[Dict] = None


class JsonFile(BaseModel):
    documents: List[Json]
