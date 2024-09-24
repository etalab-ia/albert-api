from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.config import PRIVATE_COLLECTION_TYPE, PUBLIC_COLLECTION_TYPE


class Collection(BaseModel):
    id: str
    name: Optional[str] = None
    type: Optional[Literal[PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE]] = None
    model: Optional[str] = None
    user: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class Collections(BaseModel):
    object: Literal["list"] = "list"
    data: List[Collection]


class CollectionRequest(BaseModel):
    name: str = Field(..., min_length=1)
    model: str = Field(...)

    @field_validator("name", mode="before")
    def strip(cls, v):
        if isinstance(v, str):
            v = v.strip()
        return v
