from typing import List, Literal, Optional
import json
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.variables import CHUNKERS


class ChunkerArgs(BaseModel):
    chunk_size: int = Field(512)
    chunk_overlap: int = Field(0)
    length_function: Literal["len"] = Field("len")
    is_separator_regex: bool = Field(False)
    separators: List[str] = Field(["\n\n", "\n", ". ", " "])

    # additional arguments
    chunk_min_size: int = Field(0)

    class Config:
        extra = "allow"


class Chunker(BaseModel):
    name: Optional[Literal[*CHUNKERS]] = Field(None)
    args: Optional[ChunkerArgs] = Field(None)


class FilesRequest(BaseModel):
    collection: UUID = Field(...)
    chunker: Optional[Chunker] = Field(None)

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
