import json
from typing import List, Literal
from enum import Enum
from pydantic import BaseModel, Field, model_validator


class ChunkerName(Enum):
    LANGCHAIN_RECURSIVE_CHARACTER_TEXT_SPLITTER = "LangchainRecursiveCharacterTextSplitter"
    NO_CHUNKER = "NoChunker"


class ChunkerArgs(BaseModel):
    chunk_size: int = Field(default=512, description="The size of the chunks to use for the file upload.")  # fmt: off
    chunk_overlap: int = Field(default=0, description="The overlap of the chunks to use for the file upload.")  # fmt: off
    length_function: Literal["len"] = Field(default="len", description="The function to use to calculate the length of the chunks to use for the file upload.")  # fmt: off
    is_separator_regex: bool = Field(default=False, description="Whether the separator is a regex to use for the file upload.")  # fmt: off
    separators: List[str] = Field(default=["\n\n", "\n", ". ", " "], description="The separators to use for the file upload.")  # fmt: off

    # additional arguments
    chunk_min_size: int = Field(default=0, description="The minimum size of the chunks to use for the file upload.")  # fmt: off


class Chunker(BaseModel):
    name: ChunkerName = Field(default=ChunkerName.LANGCHAIN_RECURSIVE_CHARACTER_TEXT_SPLITTER, description="The name of the chunker to use for the file upload.")  # fmt: off
    args: ChunkerArgs = Field(default_factory=ChunkerArgs, description="The arguments to use for the chunker to use for the file upload.")  # fmt: off


class FilesRequest(BaseModel):
    collection: int = Field(default=..., description="The collection ID to use for the file upload. The file will be vectorized with model defined by the collection.")  # fmt: off
    chunker: Chunker = Field(default_factory=Chunker, description="The chunker to use for the file upload.")  # fmt: off

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, values):
        if isinstance(values, str):
            return cls(**json.loads(values))
        return values
