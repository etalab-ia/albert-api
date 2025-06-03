from typing import List

from pydantic import Field

from app.schemas import BaseModel


class BaseUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0


class Detail(BaseModel):
    id: str
    model: str
    usage: BaseUsage = Field(default_factory=BaseUsage)


class Usage(BaseUsage):
    details: List[Detail] = []
