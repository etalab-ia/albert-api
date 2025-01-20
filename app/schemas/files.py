import json
from typing import Dict, List, Literal, Optional
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


class Chunker(BaseModel):
    name: Optional[Literal[*CHUNKERS]] = Field(None)
    args: Optional[ChunkerArgs] = Field(None)


class FilesRequest(BaseModel):
    collection: UUID = Field(...)
    metadata: Optional[Dict] = Field(None)
    chunker: Optional[Chunker] = Field(None)

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, values):
        if isinstance(values, str):
            return cls(**json.loads(values))
        return values

    @field_validator("collection", mode="after")
    @classmethod
    def convert_to_string(cls, collection):
        return str(collection)


class Json(BaseModel):
    title: str
    text: str
    metadata: Dict[str, str] = {}


class JsonFile(BaseModel):
    documents: List[Json]
