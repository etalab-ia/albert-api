from typing import List, Literal, Optional

from openai.types import Model
from pydantic import BaseModel

from app.schemas.core.models import ModelType


class Model(Model):
    object: Literal["model"] = "model"
    max_context_length: Optional[int] = None
    type: ModelType
    aliases: Optional[List[str]] = []


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: List[Model]
