from typing import List, Literal

from pydantic import BaseModel


class Tool(BaseModel):
    object: Literal["tool"] = "tool"
    id: str
    description: str


class Tools(BaseModel):
    object: Literal["list"] = "list"
    data: List[Tool]


class ToolOutput(BaseModel):
    prompt: str
    metadata: dict
