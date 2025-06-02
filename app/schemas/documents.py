from enum import Enum
from typing import List, Literal, Optional

from fastapi import Form
from pydantic import Field

from app.schemas import BaseModel


class ChunkerName(str, Enum):
    RECURSIVE_CHARACTER_TEXT_SPLITTER = "RecursiveCharacterTextSplitter"
    NO_SPLITTER = "NoSplitter"


CollectionForm: int = Form(default=..., description="The collection ID to use for the file upload. The file will be vectorized with model defined by the collection.")  # fmt: off
ChunkerNameForm: ChunkerName = Form(default=ChunkerName.RECURSIVE_CHARACTER_TEXT_SPLITTER, description="The name of the chunker to use for the file upload.")  # fmt: off
ChunkSizeForm: int = Form(default=2048, description="The size of the chunks to use for the file upload.")  # fmt: off
ChunkOverlapForm: int = Form(default=0, description="The overlap of the chunks to use for the file upload.")  # fmt: off
LengthFunctionForm: Literal["len"] = Form(default="len", description="The function to use to calculate the length of the chunks to use for the file upload.")  # fmt: off
IsSeparatorRegexForm: bool = Form(default=False, description="Whether the separator is a regex to use for the file upload.")  # fmt: off
SeparatorsForm: List[str] = Form(default=["\n\n", "\n", ". ", " "], description="The separators to use for the file upload.")  # fmt: off
ChunkMinSizeForm: int = Form(default=0, description="The minimum size of the chunks to use for the file upload.")  # fmt: off
MetadataForm: str = Form(default="", description="Additional metadata to chunks, JSON string.", pattern=r"^[^{}]*$")  # fmt: off


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
