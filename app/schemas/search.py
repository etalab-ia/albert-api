from enum import Enum
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.chunks import Chunk
from app.utils.exceptions import WrongSearchMethodException


class SearchMethod(str, Enum):
    HYBRID = "hybrid"
    LEXICAL = "lexical"
    SEMANTIC = "semantic"


class SearchArgs(BaseModel):
    collections: List[Any] = Field(description="List of collections ID")
    rff_k: int = Field(default=20, description="k constant in RFF algorithm")
    k: int = Field(gt=0, default=4, description="Number of results to return")
    method: SearchMethod = Field(default=SearchMethod.SEMANTIC)
    score_threshold: Optional[float] = Field(default=0.0, ge=0.0, le=1.0, description="Score of cosine similarity threshold for filtering results, only available for semantic search method.")  # fmt: off
    web_search: bool = Field(default=False, description="Whether add internet search to the results.")

    @field_validator("collections", mode="after")
    def convert_to_string(cls, collections) -> List[str]:
        return list(set(str(collection) for collection in collections))

    @model_validator(mode="after")
    def score_threshold_filter(cls, values):
        if values.score_threshold and values.method != SearchMethod.SEMANTIC:
            raise WrongSearchMethodException(detail="Score threshold is only available for semantic search method.")
        return values


class SearchRequest(SearchArgs):
    prompt: str = Field(description="Prompt related to the search")

    @field_validator("prompt")
    def blank_string(prompt) -> str:
        if prompt.strip() == "":
            raise ValueError("Prompt cannot be empty")
        return prompt


class Search(BaseModel):
    score: float
    chunk: Chunk


class Searches(BaseModel):
    object: Literal["list"] = "list"
    data: List[Search]
