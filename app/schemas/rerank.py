from typing import List, Literal

from pydantic import Field

from app.schemas import BaseModel
from app.schemas.usage import Usage


class RerankRequest(BaseModel):
    prompt: str = Field(default=..., description="The prompt to use for the reranking.")  # fmt: off
    input: List[str] = Field(default=..., description="List of input texts to rerank by relevance to the prompt.")  # fmt: off
    model: str = Field(default=..., description="The model to use for the reranking, call `/v1/models` endpoint to get the list of available models, only `text-classification` model type is supported.")  # fmt: off


class Rerank(BaseModel):
    object: Literal["rerank"] = "rerank"
    score: float
    index: int


class Reranks(BaseModel):
    id: str = Field(default=None, description="A unique identifier for the reranking.")
    object: Literal["list"] = "list"
    data: List[Rerank]
    usage: Usage = Field(default=None, description="Usage information for the request.")
