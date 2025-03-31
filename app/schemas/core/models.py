from enum import Enum


class ModelClientType(str, Enum):
    ALBERT = "albert"
    OPENAI = "openai"
    TEI = "tei"
    VLLM = "vllm"

    _SUPPORTED_MODEL_CLIENT_TYPES__EMBEDDINGS = [ALBERT, OPENAI, TEI]
    _SUPPORTED_MODEL_CLIENT_TYPES__LANGUAGE = [ALBERT, OPENAI, VLLM]
    _SUPPORTED_MODEL_CLIENT_TYPES__RERANK = [ALBERT, TEI]
    _SUPPORTED_MODEL_CLIENT_TYPES__AUDIO = [ALBERT, OPENAI]


class RoutingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    SHUFFLE = "shuffle"
