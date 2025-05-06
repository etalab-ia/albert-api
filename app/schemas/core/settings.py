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
from app.utils.variables import DEFAULT_APP_NAME, DEFAULT_TIMEOUT, ROUTERS, ROUTER__MONITORING, ROUTER__FILES


class LimitsTokenizer(str, Enum):
    TIKTOKEN_GPT2 = "tiktoken_gpt2"
    TIKTOKEN_R50K_BASE = "tiktoken_r50k_base"
    TIKTOKEN_P50K_BASE = "tiktoken_p50k_base"
    TIKTOKEN_P50K_EDIT = "tiktoken_p50k_edit"
    TIKTOKEN_CL100K_BASE = "tiktoken_cl100k_base"
    TIKTOKEN_O200K_BASE = "tiktoken_o200k_base"


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
    enable_queueing: bool = False
    clients: List[ModelClient]

    @model_validator(mode="after")
    def validate_model_type(cls, values):
        assert values.clients[0].type.value in ModelClientType.get_supported_clients(values.type.value), f"Invalid model type: {values.type.value} for client type {values.clients[0].type.value}"  # fmt: off

        return values


class WebSearch(ConfigBaseModel):
    type: WebSearchType = WebSearchType.DUCKDUCKGO
    model: str
    limited_domains: List[str] = []
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    args: dict = {}


class MultiAgentsSearch(ConfigBaseModel):
    model: str = "albert-small"
    ranker_model: str = "albert-large"
    max_tokens: int = 1024
    max_tokens_intermediate: int = 512
    extract_length: int = 512


class DatabaseQdrantArgs(ConfigBaseModel):
    prefer_grpc: bool = False

    @field_validator("prefer_grpc", mode="after")
    def force_rest(cls, prefer_grpc):
        if prefer_grpc:
            logging.warning("Qdrant does not support grpc for create index payload, force REST connection.")
            prefer_grpc = False

        return prefer_grpc


class DatabaseSQLArgs(ConfigBaseModel):
    url: str = Field(pattern=r"^postgresql|^sqlite")

    @field_validator("url", mode="after")
    def force_async(cls, url):
        if url.startswith("postgresql://"):
            logging.warning("PostgreSQL connection must be async, force asyncpg connection.")
            url = url.replace("postgresql://", "postgresql+asyncpg://")

        if url.startswith("sqlite://"):
            logging.warning("SQLite connection must be async, force aiosqlite connection.")
            url = url.replace("sqlite://", "sqlite+aiosqlite://")

        return url


class Database(ConfigBaseModel):
    type: DatabaseType
    context: str = "api"
    model: Optional[str] = None
    args: dict = {}

    @model_validator(mode="after")
    def format(cls, values):
        if values.type == DatabaseType.QDRANT:
            values.args = DatabaseQdrantArgs(**values.args).model_dump()
            assert values.model, "A text embeddings inference model ID is required for Qdrant database."

        if values.type == DatabaseType.SQL and values.context == "api":
            values.args = DatabaseSQLArgs(**values.args).model_dump()

        return values


class Usages(ConfigBaseModel):
    routers: List[Literal[*ROUTERS, "all"]] = []
    tokenizer: LimitsTokenizer = LimitsTokenizer.TIKTOKEN_O200K_BASE

    @field_validator("routers", mode="after")
    def validate_routers(cls, routers):
        if "all" in routers:
            assert len(routers) == 1, "`all` can only be used alone."
            routers = [router for router in ROUTERS]

        # exclude monitoring and files
        routers = [router for router in routers if router not in [ROUTER__MONITORING, ROUTER__FILES]]

        return routers


class Auth(ConfigBaseModel):
    master_key: str = "changeme"
    limiting_strategy: LimitingStrategy = LimitingStrategy.FIXED_WINDOW
    max_token_expiration_days: Optional[int] = Field(default=None, ge=0)


class General(ConfigBaseModel):
    # FastAPI
    title: str = DEFAULT_APP_NAME
    summary: str = "Albert API connect to your models."
    contact_name: Optional[str] = None
    contact_url: Optional[str] = None
    contact_email: Optional[str] = None
    version: str = "latest"
    description: str = "[See documentation](https://github.com/etalab-ia/albert-api/blob/main/README.md)"
    terms_of_service: Optional[str] = None
    licence_name: str = "MIT License"
    licence_identifier: str = "MIT"
    licence_url: Optional[str] = "https://raw.githubusercontent.com/etalab-ia/albert-api/refs/heads/main/LICENSE"
    openapi_url: str = "/openapi.json"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    sentry_dsn: Optional[str] = None

    # Others
    disabled_routers: List[Literal[*ROUTERS]] = []
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class Config(ConfigBaseModel):
    general: General = Field(default_factory=General)
    usages: Usages = Field(default_factory=Usages)
    auth: Auth = Field(default_factory=Auth)
    models: List[Model] = Field(min_length=1)
    databases: List[Database] = Field(min_length=1)
    web_search: List[WebSearch] = Field(default_factory=list, max_length=1)
    multi_agents_search: Optional[MultiAgentsSearch] = None

    @model_validator(mode="after")
    def validate_models(cls, values) -> Any:
        models = [model.id for model in values.models]
        aliases = [alias for model in values.models for alias in model.aliases] + models

        assert len(models) == len(set(models)), "Duplicated models name found."
        assert len(aliases) == len(set(aliases)), "Duplicated aliases found."

        return values

    @model_validator(mode="after")
    def validate_databases(cls, values) -> Any:
        redis_databases = [database for database in values.databases if database.type == DatabaseType.REDIS]
        assert len(redis_databases) <= 1, "There must be only one redis database."

        qdrant_databases = [database for database in values.databases if database.type == DatabaseType.QDRANT]
        assert len(qdrant_databases) <= 1, "There must be only one Qdrant database."

        sql_databases = [database for database in values.databases if database.type == DatabaseType.SQL and database.context == "api"]
        if len(sql_databases) > 1:
            raise ValueError("There must be only one SQL database with the `api` context. If your configuration files contains multiple SQL databases, please specify the context keyword for other SQL databases.")  # fmt: off
        if len(sql_databases) == 0:
            raise ValueError("There must be at least one SQL database.")

        values.databases = SimpleNamespace()
        values.databases.redis = redis_databases[0]
        values.databases.qdrant = qdrant_databases[0]
        values.databases.sql = sql_databases[0]

        return values


class Settings(BaseSettings):
    # legacy collections
    legacy_collections: Optional[str] = None

    @field_validator("legacy_collections", mode="after")
    def open_legacy_collections(cls, legacy_collections):
        if legacy_collections:
            logging.warning(f"Loading legacy collections from {legacy_collections}.")
            with open(file=legacy_collections, mode="r") as file:
                file_content = file.read()
                file.close()
            legacy_collections = yaml.safe_load(file_content)
        return legacy_collections

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
        with open(file=values.config_file, mode="r") as file:
            file_content = file.read()
            file.close()

        # replace environment variables (pattern: ${VARIABLE_NAME})
        for match in set(re.findall(pattern=r"\${[A-Z_]+}", string=file_content)):
            variable = match.replace("${", "").replace("}", "")
            if os.getenv(variable) is None or os.getenv(variable) == "":
                logging.warning(f"Environment variable {variable} not found or empty to replace {match}.")
            file_content = file_content.replace(match, os.getenv(variable, match))

        config = Config(**yaml.safe_load(file_content))

        values.general = config.general
        values.auth = config.auth
        values.usages = config.usages
        values.web_search = config.web_search[0] if config.web_search else None
        values.models = config.models
        values.databases = config.databases
        values.multi_agents_search = config.multi_agents_search

        if values.databases.qdrant:
            assert values.databases.sql, "SQL database is required to use Qdrant features."
            assert values.databases.qdrant.model in [model.id for model in values.models if model.type == ModelType.TEXT_EMBEDDINGS_INFERENCE], f"Qdrant model is not defined in models section with type {ModelType.TEXT_EMBEDDINGS_INFERENCE}."  # fmt: off

        if values.web_search:
            assert values.databases.qdrant, "Qdrant database is required to use web_search."
            assert values.web_search.model in [model.id for model in values.models if model.type in [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT]], f"Web search model is not defined in models section with type {ModelType.TEXT_GENERATION}."  # fmt: off

        if values.multi_agents_search:
            assert values.databases.qdrant, "Qdrant database is required to use multi-agents search."
            assert values.multi_agents_search.model in [model.id for model in values.models if model.type == ModelType.TEXT_GENERATION], f"Multi-agents search model is not defined in models section with type {ModelType.TEXT_GENERATION}."  # fmt: off

        return values
