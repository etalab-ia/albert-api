from enum import Enum
from typing import List, Literal, Optional, Union

from fastapi import Form
from langchain_text_splitters import Language
from pydantic import Field

from app.schemas import BaseModel


class Chunker(str, Enum):
    RECURSIVE_CHARACTER_TEXT_SPLITTER = "RecursiveCharacterTextSplitter"
    NO_SPLITTER = "NoSplitter"


CollectionForm: int = Form(default=..., description="The collection ID to use for the file upload. The file will be vectorized with model defined by the collection.")  # fmt: off
ChunkerForm: Chunker = Form(default=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER, description="The name of the chunker to use for the file upload.")  # fmt: off
ChunkSizeForm: int = Form(default=2048, description="The size of the chunks to use for the file upload.")  # fmt: off
ChunkOverlapForm: int = Form(default=0, description="The overlap of the chunks to use for the file upload.")  # fmt: off
LengthFunctionForm: Literal["len"] = Form(default="len", description="The function to use to calculate the length of the chunks to use for the file upload.")  # fmt: off
IsSeparatorRegexForm: bool = Form(default=False, description="Whether the separator is a regex to use for the file upload.")  # fmt: off
SeparatorsForm: List[str] = Form(default=["\n\n", "\n", ". ", " "], description="The separators to use for the file upload.")  # fmt: off
ChunkMinSizeForm: int = Form(default=0, description="The minimum size of the chunks to use for the file upload.")  # fmt: off
MetadataForm: str = Form(default="{}", description="Additional metadata to chunks, JSON string. Example: '{\"string_metadata\": \"test\", \"int_metadata\": 1, \"float_metadata\": 1.0, \"bool_metadata\": true}'", pattern=r"^\{.*\}$")  # fmt: off
LanguageSeparatorsForm: Union[Language, Literal[""]] = Form(default="", description="If provided, override separators by the code language specific separators.")  # fmt: off


class Document(BaseModel):
    object: Literal["document"] = "document"
    id: int
    name: str
    collection_id: int
    created_at: int
    chunks: Optional[int] = None


class Documents(BaseModel):
    object: Literal["list"] = "list"
    data: List[Document]


class DocumentResponse(BaseModel):
    id: int = Field(default=..., description="The ID of the document created.")
