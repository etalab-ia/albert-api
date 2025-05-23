from typing import List

from app.schemas import BaseModel


class Detail(BaseModel):
    id: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    details: List[Detail] = []
