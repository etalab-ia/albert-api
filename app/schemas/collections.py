from typing import Literal, List

from pydantic import BaseModel


class Collection(BaseModel):
    object: Literal["collection"] = "collection"
    id: str
    type: Literal["public", "private"] = "private"


class CollectionResponse(BaseModel):
    object: Literal["list"] = "list"
    data: List[Collection]
