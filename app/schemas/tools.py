from typing import Literal, List

from pydantic import BaseModel


class Tool(BaseModel):
    object: Literal["tool"] = "tool"
    id: str
    description: str


class ToolResponse(BaseModel):
    object: Literal["list"] = "list"
    data: List[Tool]

class ToolOutput(BaseModel):
    prompt: str
    metadata: dict