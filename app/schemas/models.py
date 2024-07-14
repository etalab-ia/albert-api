from typing import Literal, List

from pydantic import BaseModel
from openai.types import Model


class ModelResponse(BaseModel):
    object: Literal["list"]
    data: List[Model]
