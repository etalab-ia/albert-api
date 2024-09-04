from typing import Literal, List, Optional

from pydantic import BaseModel

from app.schemas.config import PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE

class Collection(BaseModel):
    object: Literal["collection"] = "collection"
    id: str
    name: str
    type: Literal[PUBLIC_COLLECTION_TYPE, PRIVATE_COLLECTION_TYPE]
    model: str
    user: Optional[str] = None
    description: Optional[str] = None


class Collections(BaseModel):
    object: Literal["list"] = "list"
    data: List[Collection]
