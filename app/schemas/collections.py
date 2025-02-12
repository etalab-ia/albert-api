from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.variables import COLLECTION_TYPE__PRIVATE, COLLECTION_TYPE__PUBLIC


class Collection(BaseModel):
    id: str
    name: Optional[str] = None
    type: Optional[Literal[COLLECTION_TYPE__PUBLIC, COLLECTION_TYPE__PRIVATE]] = None
    model: Optional[str] = None
    user: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[int] = None
    documents: Optional[int] = None


class Collections(BaseModel):
    object: Literal["list"] = "list"
    data: List[Collection]


class CollectionRequest(BaseModel):
    description: Optional[str] = Field(default=None, description="The description of the collection.")  # fmt: off
    name: str = Field(default=..., min_length=1, description="The name of the collection.")  # fmt: off
    model: str = Field(default=..., description="The model to use for the collection. Call `/v1/models` endpoint to get the list of available models, only `text-embeddings-inference` model type is supported.")  # fmt: off
    type: Literal[COLLECTION_TYPE__PUBLIC, COLLECTION_TYPE__PRIVATE] = Field(default=COLLECTION_TYPE__PRIVATE, description="The type of the collection. Public collections are available to all users, private collections are only available to the user who created them.")  # fmt: off

    @field_validator("name", mode="before")
    def strip(cls, name):
        if isinstance(name, str):
            name = name.strip()
        return name
