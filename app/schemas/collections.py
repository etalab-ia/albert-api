from typing import Literal, List, Optional

from pydantic import BaseModel

from app.schemas.config import PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE


class Collection(BaseModel):
    object: Literal["collection"] = "collection"
    id: str
    type: Literal[PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE]
    model: str
    user: Optional[str] = None
    description: Optional[str] = None
    created_at: int
    updated_at: int


class Collections(BaseModel):
    object: Literal["list"] = "list"
    data: List[Collection]
