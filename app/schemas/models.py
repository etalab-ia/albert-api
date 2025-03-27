from enum import Enum
from typing import List, Literal, Optional

from openai.types import Model
from pydantic import BaseModel


# TODO pass enum to model type
class ModelType(str, Enum):
    AUDIO = "automatic-speech-recognition"
    EMBEDDINGS = "text-embeddings-inference"
    LANGUAGE = "text-generation"
    RERANK = "text-classification"


class Model(Model):
    object: Literal["model"] = "model"
    max_context_length: Optional[int] = None
    type: ModelType
    aliases: Optional[List[str]] = []


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: List[Model]
