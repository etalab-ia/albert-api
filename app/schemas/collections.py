from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.variables import PRIVATE_COLLECTION_TYPE, PUBLIC_COLLECTION_TYPE


class Collection(BaseModel):
    id: str
    name: Optional[str] = None
    type: Optional[Literal[PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE]] = None
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
    type: Literal[PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE] = Field(PRIVATE_COLLECTION_TYPE)
    description: Optional[str] = Field(None)

    @field_validator("name", mode="before")
    def strip(cls, v):
        if isinstance(v, str):
            v = v.strip()
        return v
