import json
from typing import Dict, List, Literal, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.variables import COLLECTION_DISPLAY_ID__INTERNET
from app.utils.exceptions import UnsupportedFileUploadException


class ChunkerName(Enum):
    LangchainRecursiveCharacterTextSplitter = "LangchainRecursiveCharacterTextSplitter"
    NoChunker = "NoChunker"


class ChunkerArgs(BaseModel):
    chunk_size: int = Field(default=512, description="The size of the chunks to use for the file upload.")  # fmt: off
    chunk_overlap: int = Field(default=0, description="The overlap of the chunks to use for the file upload.")  # fmt: off
    length_function: Literal["len"] = Field(default="len", description="The function to use to calculate the length of the chunks to use for the file upload.")  # fmt: off
    is_separator_regex: bool = Field(default=False, description="Whether the separator is a regex to use for the file upload.")  # fmt: off
    separators: List[str] = Field(default=["\n\n", "\n", ". ", " "], description="The separators to use for the file upload.")  # fmt: off

    # additional arguments
    chunk_min_size: int = Field(default=0, description="The minimum size of the chunks to use for the file upload.")  # fmt: off


class Chunker(BaseModel):
    name: Optional[ChunkerName] = Field(default=None, description="The name of the chunker to use for the file upload.")  # fmt: off
    args: Optional[ChunkerArgs] = Field(default=None, description="The arguments to use for the chunker to use for the file upload.")  # fmt: off


class FilesRequest(BaseModel):
    collection: int = Field(default=..., description="The collection ID to use for the file upload. The file will be vectorized with model defined by the collection.")  # fmt: off
    chunker: Optional[Chunker] = Field(default=None, description="The chunker to use for the file upload.")  # fmt: off

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

    @field_validator("collection", mode="before")
    @classmethod
    def check_collection_name(cls, collection):
        if str(collection) == COLLECTION_DISPLAY_ID__INTERNET:
            raise UnsupportedFileUploadException()
        return collection


class Json(BaseModel):
    title: str
    text: str
    metadata: Dict[str, str] = {}


class JsonFile(BaseModel):
    documents: List[Json]
