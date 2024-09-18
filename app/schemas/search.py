from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


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
