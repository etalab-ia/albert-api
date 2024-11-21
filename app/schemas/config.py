import os
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from app.utils.variables import (
    EMBEDDINGS_MODEL_TYPE,
    LANGUAGE_MODEL_TYPE,
    AUDIO_MODEL_TYPE,
    INTERNET_DUCKDUCKGO_TYPE,
    INTERNET_BRAVE_TYPE,
    SEARCH_ELASTIC_TYPE,
    SEARCH_QDRANT_TYPE,
)


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
    type: Literal[SEARCH_ELASTIC_TYPE, SEARCH_QDRANT_TYPE] = SEARCH_QDRANT_TYPE
    args: dict


class CacheDB(ConfigBaseModel):
    type: Literal["redis"] = "redis"
    args: dict


class Databases(ConfigBaseModel):
    cache: CacheDB
    search: SearchDB


class Internet(ConfigBaseModel):
    type: Literal[INTERNET_DUCKDUCKGO_TYPE, INTERNET_BRAVE_TYPE] = INTERNET_DUCKDUCKGO_TYPE
    args: Optional[dict] = {}


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

    # models
    default_internet_language_model_url: Optional[str] = None
    default_internet_embeddings_model_url: Optional[str] = None

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
        if not values.default_internet_language_model_url:
            values.default_internet_language_model_url = [model.url for model in config.models if model.type == LANGUAGE_MODEL_TYPE][0]

        else:
            assert values.default_internet_language_model_url in [
                model.url for model in config.models if model.type == LANGUAGE_MODEL_TYPE
            ], "Wrong default internet language model url"

        if not values.default_internet_embeddings_model_url:
            values.default_internet_embeddings_model_url = [model.url for model in config.models if model.type == EMBEDDINGS_MODEL_TYPE][0]

        else:
            assert values.default_internet_embeddings_model_url in [
                model.url for model in config.models if model.type == EMBEDDINGS_MODEL_TYPE
            ], "Wrong default internet embeddings model url"


        values.auth = config.auth
        values.cache = config.databases.cache
        values.internet = config.internet
        values.models = config.models
        values.search = config.databases.search

        return values
