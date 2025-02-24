import os
from types import SimpleNamespace
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from app.utils.variables import (
    DATABASE_TYPE__ELASTIC,
    DATABASE_TYPE__GRIST,
    DATABASE_TYPE__QDRANT,
    DATABASE_TYPE__REDIS,
    DEFAULT_APP_NAME,
    DEFAULT_TIMEOUT,
    INTERNET_TYPE__BRAVE,
    INTERNET_TYPE__DUCKDUCKGO,
    MODEL_CLIENT_TYPE__OPENAI,
    MODEL_CLIENT_TYPE__TEI,
    MODEL_CLIENT_TYPE__VLLM,
    MODEL_TYPE__AUDIO,
    MODEL_TYPE__EMBEDDINGS,
    MODEL_TYPE__LANGUAGE,
    MODEL_TYPE__RERANK,
    ROUTER_STRATEGY__ROUND_ROBIN,
    ROUTER_STRATEGY__SHUFFLE,
    SUPPORTED_MODEL_CLIENT_TYPES__AUDIO,
    SUPPORTED_MODEL_CLIENT_TYPES__EMBEDDINGS,
    SUPPORTED_MODEL_CLIENT_TYPES__LANGUAGE,
    SUPPORTED_MODEL_CLIENT_TYPES__RERANK,
)


class ConfigBaseModel(BaseModel):
    class Config:
        extra = "allow"


class ModelClientArgs(ConfigBaseModel):
    api_url: str
    api_key: str = "EMPTY"
    timeout: int = DEFAULT_TIMEOUT

    @field_validator("api_url", mode="before")
    def validate_api_url(cls, api_url):
        api_url = api_url.rstrip("/") + "/"
        return api_url


class ModelClient(ConfigBaseModel):
    model: str
    type: Literal[MODEL_CLIENT_TYPE__OPENAI, MODEL_CLIENT_TYPE__TEI, MODEL_CLIENT_TYPE__VLLM]
    args: ModelClientArgs


class Model(ConfigBaseModel):
    id: str
    type: Literal[MODEL_TYPE__LANGUAGE, MODEL_TYPE__EMBEDDINGS, MODEL_TYPE__AUDIO, MODEL_TYPE__RERANK]
    aliases: List[str] = []
    default_internet: bool = False
    routing_strategy: Literal[ROUTER_STRATEGY__ROUND_ROBIN, ROUTER_STRATEGY__SHUFFLE] = ROUTER_STRATEGY__SHUFFLE
    clients: List[ModelClient]

    @model_validator(mode="after")
    def validate_model_type(cls, values):
        if values.type == MODEL_TYPE__EMBEDDINGS:
            assert values.clients[0].type in SUPPORTED_MODEL_CLIENT_TYPES__EMBEDDINGS, f"Invalid model type for client type {values.clients[0].type}"
        elif values.type == MODEL_TYPE__LANGUAGE:
            assert values.clients[0].type in SUPPORTED_MODEL_CLIENT_TYPES__LANGUAGE, f"Invalid model type for client type {values.clients[0].type}"
        elif values.type == MODEL_TYPE__AUDIO:
            assert values.clients[0].type in SUPPORTED_MODEL_CLIENT_TYPES__AUDIO, f"Invalid model type for client type {values.clients[0].type}"
        elif values.type == MODEL_TYPE__RERANK:
            assert values.clients[0].type in SUPPORTED_MODEL_CLIENT_TYPES__RERANK, f"Invalid model type for client type {values.clients[0].type}"

        return values


class Internet(ConfigBaseModel):
    type: Literal[INTERNET_TYPE__DUCKDUCKGO, INTERNET_TYPE__BRAVE] = INTERNET_TYPE__DUCKDUCKGO
    args: dict = {}


class Database(ConfigBaseModel):
    type: Literal[DATABASE_TYPE__REDIS, DATABASE_TYPE__QDRANT, DATABASE_TYPE__GRIST, DATABASE_TYPE__ELASTIC]
    args: dict = {}


class RateLimit(ConfigBaseModel):
    by_user: str = "100/minute"
    by_ip: str = "1000/minute"


class Config(ConfigBaseModel):
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    models: List[Model]
    databases: List[Database]
    internet: List[Internet] = Field(default=[Internet()], max_length=1)

    @model_validator(mode="after")
    def validate_models(cls, values) -> Any:
        models = [model.id for model in values.models]
        aliases = [alias for model in values.models for alias in model.aliases] + models
        language_models = [model for model in values.models if model.type == MODEL_TYPE__LANGUAGE]
        embeddings_models = [model for model in values.models if model.type == MODEL_TYPE__EMBEDDINGS]

        assert len(models) == len(set(models)), "Duplicated models name found."  # fmt: off
        assert len(aliases) == len(set(aliases)), "Duplicated aliases found."  # fmt: off
        assert len(language_models) > 0, "At least one language model is required."  # fmt: off
        assert len(embeddings_models) > 0, "At least one embeddings model is required."  # fmt: off
        assert any(model.default_internet for model in language_models), "At least one language model must be set to default_internet=True."  # fmt: off
        assert any(model.default_internet for model in embeddings_models), "At least one embeddings model must be set to default_internet=True."  # fmt: off
        assert len([model for model in language_models if model.default_internet]) == 1, "There are more than one default internet language model."  # fmt: off
        assert len([model for model in embeddings_models if model.default_internet]) == 1, "There are more than one default internet embeddings model."  # fmt: off

        return values

    @model_validator(mode="after")
    def validate_databases(cls, values) -> Any:
        cache_databases = [database for database in values.databases if database.type == DATABASE_TYPE__REDIS]
        assert len(cache_databases) == 1, "There must be only one cache database."  # fmt: off

        # check if there is only one search database
        databases = [database for database in values.databases if database.type == DATABASE_TYPE__QDRANT or database.type == DATABASE_TYPE__ELASTIC]
        assert len(databases) == 1, f"There must be only one search database ({DATABASE_TYPE__QDRANT} or {DATABASE_TYPE__ELASTIC})."  # fmt: off

        return values


class Settings(BaseSettings):
    # logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    middleware: bool = True

    # config
    config_file: str = "config.yml"

    # app
    app_name: str = DEFAULT_APP_NAME
    app_contact_url: Optional[str] = None
    app_contact_email: Optional[str] = None
    app_version: str = "0.0.0"
    app_description: str = "[See documentation](https://github.com/etalab-ia/albert-api/blob/main/README.md)"

    class Config:
        extra = "allow"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(path=config_file), "Config file not found."
        return config_file

    @model_validator(mode="after")
    def setup_config(cls, values) -> Any:
        stream = open(file=values.config_file, mode="r")
        config = Config(**yaml.safe_load(stream=stream))
        stream.close()

        values.rate_limit = config.rate_limit
        values.internet = config.internet[0]
        values.models = config.models

        values.databases = SimpleNamespace()
        values.databases.redis = next((database for database in config.databases if database.type == DATABASE_TYPE__REDIS), None)
        values.databases.qdrant = next((database for database in config.databases if database.type == DATABASE_TYPE__QDRANT), None)
        values.databases.grist = next((database for database in config.databases if database.type == DATABASE_TYPE__GRIST), None)
        values.databases.elastic = next((database for database in config.databases if database.type == DATABASE_TYPE__ELASTIC), None)

        return values
