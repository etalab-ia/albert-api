from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class Key(BaseModel):
    key: str


class Auth(BaseModel):
    type: Literal["grist"] = "grist"
    args: dict

class Model(BaseModel):
    url: str
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
    models: List[Model] = Field(..., min_items=1)
    databases: Databases
