from enum import Enum

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
    LEAST_BUSY = "least_busy"


class RoutingMode(str, Enum):
    QUEUEING = "queuing"
    NO_QUEUEING = "no_queuing"

    @classmethod
    def get_supported_strategies(cls, routing_mode):
        mapping = {
            cls.QUEUEING: [RoutingStrategy.LEAST_BUSY.value, RoutingStrategy.ROUND_ROBIN.value, RoutingStrategy.SHUFFLE.value],
            cls.NO_QUEUEING: [RoutingStrategy.ROUND_ROBIN.value, RoutingStrategy.ROUND_ROBIN.SHUFFLE.value],
        }
        return mapping.get(routing_mode, [])
