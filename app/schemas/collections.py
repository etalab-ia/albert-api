from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CollectionType(Enum):
    PRIVATE = "private"
    PUBLIC = "public"


# TODO remove model field
class CollectionRequest(BaseModel):
    name: str = Field(default=..., min_length=1, description="The name of the collection.")  # fmt: off
    description: Optional[str] = Field(default=None, description="The description of the collection.")  # fmt: off
    model: str = Field(default=..., description="The model to use for the collection. Call `/v1/models` endpoint to get the list of available models, only `text-embeddings-inference` model type is supported.")  # fmt: off
    type: CollectionType = Field(default=CollectionType.PRIVATE, description="The type of the collection. Public collections are available to all users, private collections are only available to the user who created them.")  # fmt: off

    @field_validator("name", mode="before")
    def strip_name(cls, name):
        if isinstance(name, str):
            name = name.strip()
            if not name:  # empty string
                raise ValueError("Empty string is not allowed.")

        return name


class Collection(BaseModel):
    object: Literal["collection"] = "collection"
    id: str
    name: str
    description: Optional[str] = None
    type: Optional[CollectionType] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    documents: int = 0


class Collections(BaseModel):
    object: Literal["list"] = "list"
    data: List[Collection]
