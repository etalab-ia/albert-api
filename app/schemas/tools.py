from typing import Literal, List

from pydantic import BaseModel


class Tool(BaseModel):
    id: str
    description: str
    object: Literal["tool"]


class ToolResponse(BaseModel):
    object: Literal["list"]
    data: List[Tool]
