import os
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from app.utils.variables import (
    EMBEDDINGS_MODEL_TYPE,
    LANGUAGE_MODEL_TYPE,
    AUDIO_MODEL_TYPE,
    RERANK_MODEL_TYPE,
    INTERNET_CLIENT_DUCKDUCKGO_TYPE,
    INTERNET_CLIENT_BRAVE_TYPE,
    SEARCH_CLIENT_ELASTIC_TYPE,
    SEARCH_CLIENT_QDRANT_TYPE,
)


class ConfigBaseModel(BaseModel):
    class Config:
        extra = "allow"


class Key(ConfigBaseModel):
    key: str


class Auth(ConfigBaseModel):
    type: Literal["grist"] = "grist"
    args: dict


class Model(ConfigBaseModel):
    url: str
    type: Literal[LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE, AUDIO_MODEL_TYPE, RERANK_MODEL_TYPE]
    key: Optional[str] = "EMPTY"


class SearchDB(BaseModel):
    type: Literal[SEARCH_CLIENT_ELASTIC_TYPE, SEARCH_CLIENT_QDRANT_TYPE] = SEARCH_CLIENT_QDRANT_TYPE
    args: dict


class CacheDB(ConfigBaseModel):
    type: Literal["redis"] = "redis"
    args: dict


class Databases(ConfigBaseModel):
    cache: CacheDB
    search: SearchDB


class InternetArgs(ConfigBaseModel):
    default_language_model: str
    default_embeddings_model: str

    class Config:
        extra = "allow"


class Internet(ConfigBaseModel):
    type: Literal[INTERNET_CLIENT_DUCKDUCKGO_TYPE, INTERNET_CLIENT_BRAVE_TYPE] = INTERNET_CLIENT_DUCKDUCKGO_TYPE
    args: InternetArgs


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


class Settings(BaseSettings):
    # logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # config
    config_file: str = "config.yml"

    # app
    app_name: str = "Albert API"
    app_contact_url: Optional[str] = None
    app_contact_email: Optional[str] = None
    app_version: str = "0.0.0"
    app_description: str = "[See documentation](https://github.com/etalab-ia/albert-api/blob/main/README.md)"

    # rate_limit
    global_rate_limit: str = "100/minute"
    default_rate_limit: str = "10/minute"

    class Config:
        extra = "allow"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(config_file), "Config file not found"
        return config_file

    @model_validator(mode="after")
    def setup_config(cls, values):
        config = Config(**yaml.safe_load(stream=open(file=values.config_file, mode="r")))

        values.auth = config.auth
        values.cache = config.databases.cache
        values.internet = config.internet
        values.models = config.models
        values.search = config.databases.search

        return values
