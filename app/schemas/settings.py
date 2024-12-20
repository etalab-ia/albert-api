import os
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from app.utils.variables import (
    AUDIO_MODEL_TYPE,
    EMBEDDINGS_MODEL_TYPE,
    INTERNET_CLIENT_BRAVE_TYPE,
    INTERNET_CLIENT_DUCKDUCKGO_TYPE,
    LANGUAGE_MODEL_TYPE,
    RERANK_MODEL_TYPE,
    SEARCH_CLIENT_ELASTIC_TYPE,
    SEARCH_CLIENT_QDRANT_TYPE,
)


class ConfigBaseModel(BaseModel):
    class Config:
        extra = "allow"


class RateLimit(ConfigBaseModel):
    by_key: str = "10/minute"
    by_ip: str = "100/minute"


class Internet(ConfigBaseModel):
    default_language_model: str
    default_embeddings_model: str


class Models(ConfigBaseModel):
    aliases: Dict[str, List[str]] = {}

    @field_validator("aliases", mode="before")
    def validate_aliases(cls, aliases):
        unique_aliases = list()
        for _, values in aliases.items():
            unique_aliases.extend(values)

        assert len(unique_aliases) == len(set(unique_aliases)), "Duplicated aliases found."
        return aliases


class Key(ConfigBaseModel):
    key: str


class Auth(ConfigBaseModel):
    type: Literal["grist"] = "grist"
    args: dict


class ModelClient(ConfigBaseModel):
    url: str
    type: Literal[LANGUAGE_MODEL_TYPE, EMBEDDINGS_MODEL_TYPE, AUDIO_MODEL_TYPE, RERANK_MODEL_TYPE]
    key: Optional[str] = "EMPTY"


class SearchDatabase(ConfigBaseModel):
    type: Literal[SEARCH_CLIENT_ELASTIC_TYPE, SEARCH_CLIENT_QDRANT_TYPE] = SEARCH_CLIENT_QDRANT_TYPE
    args: dict


class CacheDatabase(ConfigBaseModel):
    type: Literal["redis"] = "redis"
    args: dict


class DatabasesClient(ConfigBaseModel):
    cache: CacheDatabase
    search: SearchDatabase


class InternetClient(ConfigBaseModel):
    type: Literal[INTERNET_CLIENT_DUCKDUCKGO_TYPE, INTERNET_CLIENT_BRAVE_TYPE] = INTERNET_CLIENT_DUCKDUCKGO_TYPE
    args: dict


class Clients(ConfigBaseModel):
    auth: Optional[Auth] = None
    models: List[ModelClient] = Field(..., min_length=1)
    databases: DatabasesClient
    internet: InternetClient

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


class Config(ConfigBaseModel):
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    internet: Internet
    models: Models = Field(default_factory=Models)
    clients: Clients


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

    class Config:
        extra = "allow"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(config_file), "Config file not found"
        return config_file

    @model_validator(mode="after")
    def setup_config(cls, values):
        config = Config(**yaml.safe_load(stream=open(file=values.config_file, mode="r")))

        values.rate_limit = config.rate_limit
        values.internet = config.internet
        values.models = config.models
        values.clients = config.clients
        values.clients.cache = config.clients.databases.cache
        values.clients.search = config.clients.databases.search

        return values
