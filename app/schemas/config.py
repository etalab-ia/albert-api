from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.utils.variables import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE


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
    type: Literal[LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE]
    key: Optional[str] = "EMPTY"
    search_internet: bool = False


class VectorDB(ConfigBaseModel):
    type: Literal["qdrant"] = "qdrant"
    args: dict


class CacheDB(ConfigBaseModel):
    type: Literal["redis"] = "redis"
    args: dict


class Databases(ConfigBaseModel):
    cache: CacheDB
    vectors: VectorDB


class Config(ConfigBaseModel):
    auth: Optional[Auth] = None
    models: List[Model] = Field(..., min_length=1)
    databases: Databases

    @model_validator(mode="after")
    def validate_models(cls, values):
        language_model = False
        embeddings_model = False
        for model in values.models:
            if model.search_internet:
                if model.type == LANGUAGE_MODEL_TYPE:
                    if language_model:
                        raise ValueError("Only one language model can have search_internet=True")
                    language_model = True
                elif model.type == EMBEDDINGS_MODEL_TYPE:
                    if embeddings_model:
                        raise ValueError("Only one embeddings model can have search_internet=True")
                    embeddings_model = True

        if not language_model:
            raise ValueError("A language model with search_internet=True is required")
        if not embeddings_model:
            raise ValueError("An embeddings model with search_internet=True is required")

        return values
