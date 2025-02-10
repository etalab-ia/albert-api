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
    description: Optional[str] = None
    name: str = Field(..., min_length=1)
    model: str = Field(...)
    type: Literal[COLLECTION_TYPE__PUBLIC, COLLECTION_TYPE__PRIVATE] = Field(COLLECTION_TYPE__PRIVATE)
    description: Optional[str] = Field(None)

    @field_validator("name", mode="before")
    def strip(cls, name):
        if isinstance(name, str):
            name = name.strip()
        return name
