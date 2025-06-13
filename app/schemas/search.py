from enum import Enum
from typing import Any, List, Literal, Optional

from pydantic import Field, field_validator, model_validator

from app.schemas import BaseModel
from app.schemas.chunks import Chunk
from app.schemas.usage import Usage
from app.utils.exceptions import WrongSearchMethodException


class SearchMethod(str, Enum):
    """Enum representing the search methods available (will be displayed in this order in playground)."""

    MULTIAGENT = "multiagent"
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    LEXICAL = "lexical"


class SearchArgs(BaseModel):
    collections: List[Any] = Field(default=[], description="List of collections ID")
    rff_k: int = Field(default=20, description="k constant in RFF algorithm")
    k: int = Field(gt=0, default=4, description="Number of results to return")
    method: SearchMethod = Field(default=SearchMethod.SEMANTIC)
    score_threshold: Optional[float] = Field(default=0.0, ge=0.0, le=1.0, description="Score of cosine similarity threshold for filtering results, only available for semantic search method.")  # fmt: off
    web_search: bool = Field(default=False, description="Whether add internet search to the results.")
    web_search_k: int = Field(default=5, description="Number of results to return for web search.")

    @model_validator(mode="after")
    def score_threshold_filter(cls, values):
        if values.score_threshold and values.method not in (SearchMethod.SEMANTIC, SearchMethod.MULTIAGENT):
            raise WrongSearchMethodException(detail="Score threshold is only available for semantic and multiagent search methods.")
        return values


class SearchRequest(SearchArgs):
    prompt: str = Field(description="Prompt related to the search")

    @field_validator("prompt")
    def blank_string(prompt) -> str:
        if prompt.strip() == "":
            raise ValueError("Prompt cannot be empty")
        return prompt


class Search(BaseModel):
    method: SearchMethod
    score: float
    chunk: Chunk


class Searches(BaseModel):
    object: Literal["list"] = "list"
    data: List[Search]
    usage: Usage = Field(default=None, description="Usage information for the request.")
