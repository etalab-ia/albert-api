from typing import List, Literal, Optional

from pydantic import BaseModel

from app.schemas.config import PRIVATE_COLLECTION_TYPE, PUBLIC_COLLECTION_TYPE


class Collection(BaseModel):
    object: Literal["collection"] = "collection"
    id: str  # name
    type: Literal[PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE]
    model: str
    user: Optional[str] = None
    description: Optional[str] = None
    created_at: int
    updated_at: int


class Collections(BaseModel):
    object: Literal["list"] = "list"
    data: List[Collection]


class CollectionMetadata(BaseModel):
    id: str
    name: Optional[str] = None
    type: Optional[Literal[PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE]] = None
    model: Optional[str] = None
    user: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
