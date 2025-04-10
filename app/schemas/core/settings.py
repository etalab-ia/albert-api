from enum import Enum
import logging
import os
import re
from types import SimpleNamespace
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from app.schemas.core.auth import LimitingStrategy
from app.schemas.core.models import ModelClientType, RoutingStrategy
from app.schemas.models import ModelType
from app.utils.variables import DEFAULT_APP_NAME, DEFAULT_TIMEOUT, ROUTERS


class DatabaseType(str, Enum):
    QDRANT = "qdrant"
    REDIS = "redis"
    SQL = "sql"


class WebSearchType(str, Enum):
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
        if values.type == ModelType.TEXT_EMBEDDINGS_INFERENCE:
            assert values.clients[0].type in ModelClientType._SUPPORTED_MODEL_CLIENT_TYPES__EMBEDDINGS, f"Invalid model type for client type {values.clients[0].type}"  # fmt: off
        elif values.type == ModelType.TEXT_GENERATION:
            assert values.clients[0].type in ModelClientType._SUPPORTED_MODEL_CLIENT_TYPES__LANGUAGE, f"Invalid model type for client type {values.clients[0].type}"  # fmt: off
        elif values.type == ModelType.AUTOMATIC_SPEECH_RECOGNITION:
            assert values.clients[0].type in ModelClientType._SUPPORTED_MODEL_CLIENT_TYPES__AUDIO, f"Invalid model type for client type {values.clients[0].type}"  # fmt: off
        elif values.type == ModelType.TEXT_CLASSIFICATION:
            assert values.clients[0].type in ModelClientType._SUPPORTED_MODEL_CLIENT_TYPES__RERANK, f"Invalid model type for client type {values.clients[0].type}"  # fmt: off
        else:
            raise ValueError(f"Invalid model type: {values.type}")

        return values


class WebSearch(ConfigBaseModel):
    type: WebSearchType = WebSearchType.DUCKDUCKGO
    model: str
    args: dict = {}


class DatabaseQdrant(ConfigBaseModel):
    model: str
    args: dict = {}


class Database(ConfigBaseModel):
    type: DatabaseType
    model: Optional[str] = None
    args: dict = {}

    @model_validator(mode="after")
    def qdrant(cls, values):
        # Qdrant does not support grpc for create index payload
        if values.type == DatabaseType.QDRANT:
            if values.args.get("prefer_grpc"):
                logging.warning("Qdrant does not support grpc for create index payload, force REST connection.")
            values.args["prefer_grpc"] = False

            assert values.model, "A text embeddings inference model ID is required for Qdrant database."

        return values


class Auth(ConfigBaseModel):
    master_key: str = "changeme"
    limiting_strategy: LimitingStrategy = LimitingStrategy.FIXED_WINDOW


class General(ConfigBaseModel):
    app_name: str = DEFAULT_APP_NAME
    app_contact_url: Optional[str] = None
    app_contact_email: Optional[str] = None
    app_version: str = "0.0.0"
    app_description: str = "[See documentation](https://github.com/etalab-ia/albert-api/blob/main/README.md)"
    disabled_routers: List[Literal[*ROUTERS]] = []
    disabled_middleware: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class Config(ConfigBaseModel):
    general: General = Field(default_factory=General)
    auth: Auth = Field(default_factory=Auth)
    models: List[Model] = Field(min_length=1)
    databases: List[Database] = Field(min_length=1)
    web_search: List[WebSearch] = Field(default_factory=list, max_length=1)

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
    # config
    config_file: str = "config.yml"

    class Config:
        extra = "allow"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(path=config_file), "Config file not found."
        return config_file

    @model_validator(mode="after")
    def setup_config(cls, values) -> Any:
        with open(file=values.config_file, mode="r") as f:
            file_content = f.read()
            f.close()

        # replace environment variables (pattern: ${VARIABLE_NAME})
        for match in set(re.findall(pattern=r"\${[A-Z_]+}", string=file_content)):
            variable = match.replace("${", "").replace("}", "")
            assert os.getenv(variable), f"Environment variable {variable} not found or empty to replace {match}."
            file_content = file_content.replace(match, os.environ[variable])

        config = Config(**yaml.safe_load(file_content))

        values.general = config.general
        values.auth = config.auth
        values.web_search = config.web_search[0] if config.web_search else None
        values.models = config.models

        values.databases = SimpleNamespace()
        values.databases.sql = next((database for database in config.databases if database.type == DatabaseType.SQL), None)
        values.databases.redis = next((database for database in config.databases if database.type == DatabaseType.REDIS), None)
        values.databases.qdrant = next((database for database in config.databases if database.type == DatabaseType.QDRANT), None)

        assert values.databases.sql.args["url"].startswith("postgresql+asyncpg://") or values.databases.sql.args["url"].startswith("sqlite+aiosqlite://"), "SQL connection must be async."  # fmt: off

        if values.databases.qdrant:
            assert values.databases.sql, "SQL database is required to use Qdrant features."
            assert values.databases.qdrant.model in [model.id for model in values.models if model.type == ModelType.TEXT_EMBEDDINGS_INFERENCE], f"Qdrant model is not defined in models section with type {ModelType.TEXT_EMBEDDINGS_INFERENCE}."  # fmt: off

        if values.web_search:
            assert values.databases.qdrant, "Qdrant database is required to use web_search."
            assert values.web_search.model in [model.id for model in values.models if model.type == ModelType.TEXT_GENERATION], f"Web search model is not defined in models section with type {ModelType.TEXT_GENERATION}."  # fmt: off

        return values
