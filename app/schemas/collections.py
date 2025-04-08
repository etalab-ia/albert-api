from enum import Enum
from typing import List, Literal, Optional

from pydantic import Field, field_validator

from app.schemas import BaseModel


class CollectionVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class CollectionRequest(BaseModel):
    name: str = Field(min_length=1, description="The name of the collection.")
    description: Optional[str] = Field(default=None, description="The description of the collection.")
    visibility: CollectionVisibility = Field(default=CollectionVisibility.PRIVATE, description="The type of the collection. Public collections are available to all users, private collections are only available to the user who created them.")  # fmt: off

    @field_validator("name", mode="after")
    def strip_name(cls, name):
        if isinstance(name, str):
            name = name.strip()
            if not name:  # empty string
                raise ValueError("Name cannot be empty.")

        return name


class CollectionUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, description="The name of the collection.")
    description: Optional[str] = Field(default=None, description="The description of the collection.")
    visibility: Optional[CollectionVisibility] = Field(default=None, description="The type of the collection. Public collections are available to all users, private collections are only available to the user who created them.")  # fmt: off

    @field_validator("name", mode="after")
    def strip_name(cls, name):
        if isinstance(name, str):
            name = name.strip()
            if not name:  # empty string
                raise ValueError("Name cannot be empty.")

        return name


class Collection(BaseModel):
    object: Literal["collection"] = "collection"
    id: int
    name: str
    owner: str
    description: Optional[str] = None
    visibility: Optional[CollectionVisibility] = None
    created_at: int
    updated_at: int
    documents: int = 0


class Collections(BaseModel):
    object: Literal["list"] = "list"
    data: List[Collection]
