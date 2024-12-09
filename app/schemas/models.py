from typing import List, Literal, Optional

from openai.types import Model
from pydantic import BaseModel

from app.utils.variables import AUDIO_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE, RERANK_MODEL_TYPE


class Model(Model):
    max_context_length: Optional[int] = None
    type: Literal[LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE, AUDIO_MODEL_TYPE, RERANK_MODEL_TYPE]
    status: Literal["available", "unavailable"]


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: List[Model]
