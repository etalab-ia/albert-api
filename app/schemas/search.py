from typing import List, Literal, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.schemas.chunks import Chunk
from app.utils.variables import INTERNET_COLLECTION_ID


class SearchRequest(BaseModel):
    prompt: str
    collections: List[Union[UUID, Literal[INTERNET_COLLECTION_ID]]]
    k: int = Field(gt=0, description="Number of results to return")
    score_threshold: Optional[float] = None

    @field_validator("prompt")
    def blank_string(value):
        if value.strip() == "":
            raise ValueError("Prompt cannot be empty")
        return value

    @field_validator("collections")
    def convert_to_string(cls, v):
        if v is None:
            return []
        return list(set(str(collection) for collection in v))


class Search(BaseModel):
    score: float
    chunk: Chunk


class Searches(BaseModel):
    object: Literal["list"] = "list"
    data: List[Search]
