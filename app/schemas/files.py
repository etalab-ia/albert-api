from typing import List, Literal, Optional
import json
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.variables import CHUNKERS, SUPPORTED_FILE_TYPES


class File(BaseModel):
    object: Literal["file"] = "file"
    id: str
    bytes: int
    name: str
    chunks: list = []
    created_at: int


class Files(BaseModel):
    object: Literal["list"] = "list"
    data: List[File]


class ChunkerArgs(BaseModel):
    chunk_size: int = Field(512)
    chunk_overlap: int = Field(0)
    length_function: Literal["len"] = Field("len")
    is_separator_regex: bool = Field(False)
    separators: List[str] = Field(["\n\n", "\n", ". ", " "])

    # additional arguments
    chunk_min_size: Optional[int] = Field(0)


class Chunker(BaseModel):
    name: Optional[Literal[*CHUNKERS]] = Field(None)
    args: Optional[ChunkerArgs] = Field(None)


class FilesRequest(BaseModel):
    collection: UUID = Field(...)
    chunker: Optional[Chunker] = Field(None)
    file_type: Optional[Literal[*SUPPORTED_FILE_TYPES]] = None

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value

    @field_validator("collection", mode="after")
    @classmethod
    def convert_to_string(cls, value):
        return str(value)


class Json(BaseModel):
    title: str
    text: str
    metadata: dict = {}


class JsonFile(BaseModel):
    documents: List[Json]
