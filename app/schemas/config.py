from typing import List, Optional, Literal

from pydantic import BaseModel, Field

# Variables
METADATA_COLLECTION = "collections"
PUBLIC_COLLECTION_TYPE = "public"
PRIVATE_COLLECTION_TYPE = "private"
EMBEDDINGS_MODEL_TYPE = "text-embeddings-inference"
LANGUAGE_MODEL_TYPE = "text-generation"
AUDIO_MODEL_TYPE = "audio-transcription"


class Key(BaseModel):
    key: str


class Auth(BaseModel):
    type: Literal["grist"] = "grist"
    args: dict


class Model(BaseModel):
    url: str
    type: Literal[LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE, AUDIO_MODEL_TYPE]
    key: Optional[str] = "EMPTY"


class VectorDB(BaseModel):
    type: Literal["qdrant"] = "qdrant"
    args: dict


class CacheDB(BaseModel):
    type: Literal["redis"] = "redis"
    args: dict


class FilesDB(BaseModel):
    type: Literal["minio"] = "minio"
    args: dict


class Databases(BaseModel):
    cache: CacheDB
    vectors: VectorDB
    files: FilesDB


class Config(BaseModel):
    auth: Optional[Auth] = None
    models: List[Model] = Field(..., min_length=1)
    databases: Databases
