from enum import Enum

from app.schemas.models import ModelType
from pydantic import BaseModel, Field


class ModelClientBudget(BaseModel):
    prompt_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")
    completion_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")


class ModelClientType(str, Enum):
    ALBERT = "albert"
    OPENAI = "openai"
    TEI = "tei"
    VLLM = "vllm"

    @classmethod
    def get_supported_clients(cls, model_type):
        mapping = {
            ModelType.AUTOMATIC_SPEECH_RECOGNITION: [cls.ALBERT.value, cls.OPENAI.value],
            ModelType.IMAGE_TEXT_TO_TEXT: [cls.ALBERT.value, cls.OPENAI.value, cls.VLLM.value],
            ModelType.TEXT_EMBEDDINGS_INFERENCE: [cls.ALBERT.value, cls.OPENAI.value, cls.TEI.value],
            ModelType.TEXT_GENERATION: [cls.ALBERT.value, cls.OPENAI.value, cls.VLLM.value],
            ModelType.TEXT_CLASSIFICATION: [cls.ALBERT.value, cls.TEI.value],
        }
        return mapping.get(model_type, [])


class RoutingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    SHUFFLE = "shuffle"
