from typing import List, Literal

from openai.types import Model
from pydantic import BaseModel

from app.schemas.config import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE


class Model(Model):
    type: Literal[LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE]


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: List[Model]
