from typing import List, Literal

from pydantic import BaseModel


class RerankRequest(BaseModel):
    prompt: str
    input: List[str]
    model: str


class Rerank(BaseModel):
    score: float
    index: int


class Reranks(BaseModel):
    object: Literal["list"] = "list"
    data: List[Rerank]
