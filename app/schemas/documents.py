from typing import Literal, List, Optional

from app.schemas import BaseModel


class Document(BaseModel):
    object: Literal["document"] = "document"
    id: int
    name: str
    collection_id: int
    created_at: int
    chunks: Optional[int] = None


class Documents(BaseModel):
    object: Literal["list"] = "list"
    data: List[Document]
