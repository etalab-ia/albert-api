from typing import Literal, List

from pydantic import BaseModel
from openai.types import Model

from app.schemas.config import LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE


class Model(Model):
    type: Literal[LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE]


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: List[Model]
