from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.chunks import Chunk


class SearchRequest(BaseModel):
    prompt: str
    model: str
    collections: List[str]
    k: int = Field(gt=0, description="Number of results to return")
    score_threshold: Optional[float] = None

    @field_validator("prompt")
    def blank_string(value):
        if value.strip() == "":
            raise ValueError("Prompt cannot be empty")
        return value


class Search(BaseModel):
    score: float
    chunk: Chunk


class Searches(BaseModel):
    object: Literal["list"] = "list"
    data: List[Search]
