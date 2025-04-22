from enum import Enum
from typing import Any, List, Literal, Optional

from pydantic import Field, field_validator, model_validator

from app.schemas import BaseModel
from app.schemas.chunks import Chunk
from app.utils.exceptions import WrongSearchMethodException, CollectionNotFoundException


class SearchMethod(str, Enum):
    HYBRID = "hybrid"
    LEXICAL = "lexical"
    SEMANTIC = "semantic"
    MULTIAGENT = "multiagent"


class SearchArgs(BaseModel):
    collections: List[Any] = Field(description="List of collections ID", min_length=1)
    rff_k: int = Field(default=20, description="k constant in RFF algorithm")
    k: int = Field(gt=0, default=4, description="Number of results to return")
    method: SearchMethod = Field(default=SearchMethod.SEMANTIC)
    score_threshold: Optional[float] = Field(default=0.0, ge=0.0, le=1.0, description="Score of cosine similarity threshold for filtering results, only available for semantic search method.")  # fmt: off
    web_search: bool = Field(default=False, description="Whether add internet search to the results.")

    @model_validator(mode="after")
    def score_threshold_filter(cls, values):
        if values.score_threshold and values.method != SearchMethod.SEMANTIC:
            raise WrongSearchMethodException(detail="Score threshold is only available for semantic search method.")
        return values

    @field_validator("collections", mode="before")
    def legacy_collections(cls, collections):
        from app.utils.settings import settings

        _collections = []
        for collection in collections:
            if isinstance(collection, int):
                _collections.append(collection)
            elif settings.legacy_collections:
                _collection = settings.legacy_collections.get(collection)
                if _collection:
                    _collections.append(_collection)
                else:
                    raise CollectionNotFoundException(detail=f"Collection {collection} not found.")
            else:
                raise CollectionNotFoundException(detail=f"Collection {collection} not found.")

            collections = _collections

        return collections


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
