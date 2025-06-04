from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.schemas.models import ModelType


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

class ModelClientCarbonImpactParams(BaseModel):
    total: Optional[int] = None 
    active: Optional[int] = None 