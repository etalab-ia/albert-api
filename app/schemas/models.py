from typing import List, Literal, Optional

from openai.types import Model
from pydantic import BaseModel

from app.utils.variables import MODEL_TYPE__AUDIO, MODEL_TYPE__EMBEDDINGS, MODEL_TYPE__LANGUAGE, MODEL_TYPE__RERANK


# TODO pass enum to model type
class Model(Model):
    object: Literal["model"] = "model"
    max_context_length: Optional[int] = None
    type: Optional[Literal[MODEL_TYPE__LANGUAGE, MODEL_TYPE__EMBEDDINGS, MODEL_TYPE__AUDIO, MODEL_TYPE__RERANK]] = None
    aliases: Optional[List[str]] = []


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: List[Model]
