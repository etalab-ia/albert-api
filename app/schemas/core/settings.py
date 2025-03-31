from enum import Enum
import os
from types import SimpleNamespace
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from app.schemas.core.auth import LimitingStrategy
from app.schemas.core.models import ModelClientType, ModelType, RoutingStrategy
from app.utils.variables import DEFAULT_APP_NAME, DEFAULT_TIMEOUT, ROUTERS


class DatabaseType(str, Enum):
    QDRANT = "qdrant"
    REDIS = "redis"
    SQL = "sql"


class InternetType(str, Enum):
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"


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
    type: ModelClientType
    args: ModelClientArgs


class Model(ConfigBaseModel):
    id: str
    type: ModelType
    aliases: List[str] = []
    owned_by: str = DEFAULT_APP_NAME
    routing_strategy: RoutingStrategy = RoutingStrategy.SHUFFLE
    clients: List[ModelClient]

    @model_validator(mode="after")
    def validate_model_type(cls, values):
        if values.type == ModelType.EMBEDDINGS:
            assert values.clients[0].type in ModelClientType._SUPPORTED_MODEL_CLIENT_TYPES__EMBEDDINGS, f"Invalid model type for client type {values.clients[0].type}"  # fmt: off
        elif values.type == ModelType.LANGUAGE:
            assert values.clients[0].type in ModelClientType._SUPPORTED_MODEL_CLIENT_TYPES__LANGUAGE, f"Invalid model type for client type {values.clients[0].type}"  # fmt: off
        elif values.type == ModelType.AUDIO:
            assert values.clients[0].type in ModelClientType._SUPPORTED_MODEL_CLIENT_TYPES__AUDIO, f"Invalid model type for client type {values.clients[0].type}"  # fmt: off
        elif values.type == ModelType.RERANK:
            assert values.clients[0].type in ModelClientType._SUPPORTED_MODEL_CLIENT_TYPES__RERANK, f"Invalid model type for client type {values.clients[0].type}"  # fmt: off
        else:
            raise ValueError(f"Invalid model type: {values.type}")

        return values


class Internet(ConfigBaseModel):
    type: InternetType = InternetType.DUCKDUCKGO
    args: dict = {}


class Database(ConfigBaseModel):
    type: DatabaseType
    args: dict = {}


class Auth(ConfigBaseModel):
    master_key: str = "changeme"
    limiting_strategy: LimitingStrategy = LimitingStrategy.FIXED_WINDOW


class General(ConfigBaseModel):
    internet_model: str
    documents_model: str


class Config(ConfigBaseModel):
    general: General
    auth: Auth = Field(default_factory=Auth)
    models: List[Model] = Field(min_length=1)
    databases: List[Database] = Field(min_length=1)
    internet: List[Internet] = Field(default_factory=list, max_length=1)

    @model_validator(mode="after")
    def validate_models(cls, values) -> Any:
        models = [model.id for model in values.models]
        aliases = [alias for model in values.models for alias in model.aliases] + models

        assert len(models) == len(set(models)), "Duplicated models name found."
        assert len(aliases) == len(set(aliases)), "Duplicated aliases found."

        return values

    @model_validator(mode="after")
    def validate_databases(cls, values) -> Any:
        cache_databases = [database for database in values.databases if database.type == DatabaseType.REDIS]
        assert len(cache_databases) == 1, "There must be only one cache database."

        return values


class Settings(BaseSettings):
    # logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # middleware on/off
    disabled_middleware: bool = False

    # config
    config_file: str = "config.yml"

    # disabled endpoints
    disabled_routers: List[Literal[*ROUTERS]] = Field(default_factory=list)

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

        values.general = config.general
        values.auth = config.auth
        values.internet = config.internet[0]
        values.models = config.models

        values.databases = SimpleNamespace()
        values.databases.sql = next((database for database in config.databases if database.type == DatabaseType.SQL), None)
        values.databases.redis = next((database for database in config.databases if database.type == DatabaseType.REDIS), None)
        values.databases.qdrant = next((database for database in config.databases if database.type == DatabaseType.QDRANT), None)

        if values.databases.qdrant:
            assert values.general.documents_model in [model.id for model in values.models if model.type == ModelType.EMBEDDINGS], f"Documents model is not defined in models section with type {ModelType.EMBEDDINGS}."  # fmt: off

        if values.internet:
            assert values.databases.qdrant, "Qdrant database is required to use internet."
            assert values.general.internet_model in [model.id for model in values.models if model.type == ModelType.LANGUAGE], f"Internet model is not defined in models section with type {ModelType.LANGUAGE}."  # fmt: off

        return values
