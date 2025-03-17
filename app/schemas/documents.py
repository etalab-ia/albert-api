from typing import Literal, List

from pydantic import BaseModel


class Document(BaseModel):
    object: Literal["document"] = "document"
    id: str
    name: str
    created_at: int
    updated_at: int
    chunks: int = 0


class Documents(BaseModel):
    object: Literal["list"] = "list"
    data: List[Document]
