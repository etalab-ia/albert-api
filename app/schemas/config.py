from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.utils.variables import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE


class Key(BaseModel):
    key: str


class Auth(BaseModel):
    type: Literal["grist"] = "grist"
    args: dict


class Model(BaseModel):
    url: str
    type: Literal[LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE]
    key: Optional[str] = "EMPTY"
    search_internet: bool = False


class VectorDB(BaseModel):
    type: Literal["qdrant"] = "qdrant"
    args: dict


class CacheDB(BaseModel):
    type: Literal["redis"] = "redis"
    args: dict


class Databases(BaseModel):
    cache: CacheDB
    vectors: VectorDB


class Config(BaseModel):
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
