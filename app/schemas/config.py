from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.utils.variables import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE, AUDIO_MODEL_TYPE


class ConfigBaseModel(BaseModel):
    class Config:
        extra = "forbid"


class Key(ConfigBaseModel):
    key: str


class Auth(ConfigBaseModel):
    type: Literal["grist"] = "grist"
    args: dict


class Model(ConfigBaseModel):
    url: str
    type: Literal[LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE, AUDIO_MODEL_TYPE]
    key: Optional[str] = "EMPTY"


class SearchDB(BaseModel):
    type: Literal["elastic", "qdrant"] = "qdrant"
    args: dict


class CacheDB(ConfigBaseModel):
    type: Literal["redis"] = "redis"
    args: dict


class Databases(ConfigBaseModel):
    cache: CacheDB
    search: SearchDB


class Internet(ConfigBaseModel):
    method: Literal["duckduckgo", "brave"] = "brave"
    api_key: str


class Config(ConfigBaseModel):
    auth: Optional[Auth] = None
    models: List[Model] = Field(..., min_length=1)
    databases: Databases
    internet: Optional[Internet] = None

    @model_validator(mode="after")
    def validate_models(cls, values):
        language_model = False
        embeddings_model = False
        for model in values.models:
            if model.type == LANGUAGE_MODEL_TYPE:
                language_model = True
            elif model.type == EMBEDDINGS_MODEL_TYPE:
                embeddings_model = True

        if not language_model:
            raise ValueError("At least one language model is required")
        if not embeddings_model:
            raise ValueError("At least one embeddings model is required")

        return values
