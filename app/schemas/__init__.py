from pydantic import BaseModel


class BaseModel(BaseModel):
    class Config:
        extra = "allow"
