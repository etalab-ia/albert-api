from pydantic import BaseModel


class BaseModel(BaseModel):
    class Config:
        extra = "allow"


class Usage(BaseModel):
    prompt_tokens: int
    total_tokens: int
