from enum import Enum
from typing import List, Literal, Optional

from openai.types import Model
from pydantic import BaseModel


class ModelType(str, Enum):
    AUTOMATIC_SPEECH_RECOGNITION = "automatic-speech-recognition"
    TEXT_EMBEDDINGS_INFERENCE = "text-embeddings-inference"
    TEXT_GENERATION = "text-generation"
    TEXT_CLASSIFICATION = "text-classification"


class Model(Model):
    object: Literal["model"] = "model"
    max_context_length: Optional[int] = None
    type: ModelType
    aliases: Optional[List[str]] = []


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: List[Model]
