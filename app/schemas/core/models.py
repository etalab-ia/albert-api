from enum import Enum


class ModelType(str, Enum):
    AUDIO = "automatic-speech-recognition"
    EMBEDDINGS = "text-embeddings-inference"
    LANGUAGE = "text-generation"
    RERANK = "text-classification"


class RoutingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    SHUFFLE = "shuffle"
