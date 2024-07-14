from typing import List, Optional, Literal

from pydantic import BaseModel, Field, validator


class Key(BaseModel):
    key: str


class Auth(BaseModel):
    keys: List[Key]
    salt: str

    @validator("keys")
    def validate_keys(cls, v):
        if v is None:
            raise ValueError("At least one key must be specified if keys section is present")
        return v

class Model(BaseModel):
    url: str
    key: Optional[str] = "EMPTY"


class VectorDB(BaseModel):
    type: Literal["qdrant"]
    args: dict


class ChatHistoryDB(BaseModel):
    type: Literal["redis"]
    args: dict


class FilesDB(BaseModel):
    type: Literal["minio"]
    args: dict


class Databases(BaseModel):
    chathistory: ChatHistoryDB
    vectors: VectorDB
    files: FilesDB


class Config(BaseModel):
    auth: Auth
    models: List[Model] = Field(..., min_items=1)
    databases: Databases
