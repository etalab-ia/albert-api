from typing import Optional

from pydantic import BaseModel


class BaseModel(BaseModel):
    class Config:
        extra = "allow"


class Usage(BaseModel):
    prompt_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
