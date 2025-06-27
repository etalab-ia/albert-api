from enum import Enum
import logging
import os
import re
from types import SimpleNamespace
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from app.schemas.core.auth import LimitingStrategy
from app.schemas.core.models import ModelClientType, RoutingStrategy
from app.schemas.core.usage import CountryCodes
from app.schemas.models import ModelCosts, ModelType
from app.schemas.search import SearchMethod
from app.utils.variables import DEFAULT_APP_NAME, DEFAULT_TIMEOUT, ROUTERS


class LimitsTokenizer(str, Enum):
    TIKTOKEN_GPT2 = "tiktoken_gpt2"
    TIKTOKEN_R50K_BASE = "tiktoken_r50k_base"
    TIKTOKEN_P50K_BASE = "tiktoken_p50k_base"
    TIKTOKEN_P50K_EDIT = "tiktoken_p50k_edit"
    TIKTOKEN_CL100K_BASE = "tiktoken_cl100k_base"
    TIKTOKEN_O200K_BASE = "tiktoken_o200k_base"


class DatabaseType(str, Enum):
    QDRANT = "qdrant"
    ELASTICSEARCH = "elasticsearch"
    REDIS = "redis"
    SQL = "sql"


class WebSearchType(str, Enum):
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"


class ParserType(str, Enum):
    ALBERT = "albert"
    MARKER = "marker"


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ParserArgs(ConfigBaseModel):
    api_url: str
    api_key: Optional[str] = None
    timeout: int = DEFAULT_TIMEOUT


class Parser(ConfigBaseModel):
    type: ParserType = ParserType.MARKER
    args: ParserArgs


class ModelClientArgs(ConfigBaseModel):
    api_url: str
    api_key: str = "EMPTY"
    timeout: int = DEFAULT_TIMEOUT

    @field_validator("api_url", mode="before")
    def validate_api_url(cls, api_url):
        api_url = api_url.rstrip("/") + "/"

        return api_url


class ModelClientCarbonFootprint(ConfigBaseModel):
    model_zone: CountryCodes = CountryCodes.WOR  # world is the default zone
    total_params: Optional[int] = None
    active_params: Optional[int] = None

    @model_validator(mode="after")
    def complete_params(cls, values):
        if values.total_params is None and values.active_params is not None:
            values.total_params = values.active_params
        if values.active_params is None and values.total_params is not None:
            values.active_params = values.total_params

        return values


class ModelClient(ConfigBaseModel):
    model: str
    type: ModelClientType
    costs: ModelCosts = Field(default_factory=ModelCosts)
    carbon: ModelClientCarbonFootprint = Field(default_factory=ModelClientCarbonFootprint)
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
        assert values.clients[0].type.value in ModelClientType.get_supported_clients(values.type.value), f"Invalid model type: {values.type.value} for client type {values.clients[0].type.value}"  # fmt: off

        if values.type not in [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT]:
            for client in values.clients:
                if client.carbon.active_params is not None:
                    logging.warning(f"Carbon footprint is not supported for {values.type.value} models, set active params to None.")
                    client.carbon.active_params = None
                if client.carbon.total_params is not None:
                    logging.warning(f"Carbon footprint is not supported for {values.type.value} models, set total params to None.")
                    client.carbon.total_params = None

        return values


class WebSearchClientDuckDuckGoArgs(ConfigBaseModel):
    """
    All additionnal parameters for the DuckDuckGo API requests can be found here: https://www.searchapi.io/docs/duckduckgo-api
    """

    api_key: Optional[str] = Field(default=None, description="API key to use for the DuckDuckGo API requests.")
    timeout: int = Field(default=DEFAULT_TIMEOUT, description="Timeout for the DuckDuckGo API requests.")


class WebSearchClientBraveArgs(ConfigBaseModel):
    """
    All additionnal parameters for the Brave API requests can be found here: https://api-dashboard.search.brave.com/app/documentation/web-search/query
    """

    api_key: str = Field(description="API key to use for the Brave API requests.")
    timeout: int = Field(default=DEFAULT_TIMEOUT, description="Timeout for the Brave API requests.")


class WebSearchClient(ConfigBaseModel):
    """
    Web search client configuration (API of the search engine to use).
    """

    type: WebSearchType = Field(default=WebSearchType.DUCKDUCKGO, description="Type of web search client to use.")
    args: Union[WebSearchClientDuckDuckGoArgs, WebSearchClientBraveArgs] = Field(default_factory=WebSearchClientDuckDuckGoArgs, description="Arguments for the web search client.")  # fmt: off


class WebSearch(ConfigBaseModel):
    """
    Albert API allows searching the internet to enrich API responses. For this, it is necessary to configure a search engine API client in the `web_search` section.

    Prerequisites:
    - a vector database
    - a text-generation or image-text-to-text model
    """

    query_model: str = Field(description="Model to use to generate the web query, only text-generation and image-text-to-text models are supported.")
    limited_domains: List[str] = Field(default_factory=list, description="List of domains to limit the web search to.")
    user_agent: Optional[str] = Field(default=None, description="User agent to use for the scrapping requests.")
    client: WebSearchClient = Field(default_factory=WebSearchClient, description="Web search client to use.")


class MultiAgentsSearch(ConfigBaseModel):
    model: str = "albert-small"
    ranker_model: str = "albert-large"
    max_tokens: int = 1024
    max_tokens_intermediate: int = 512
    extract_length: int = 512
    method: SearchMethod = SearchMethod.SEMANTIC


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


class MonitoringSentryArgs(ConfigBaseModel):
    dsn: str = Field(description="If Sentry DSN is set, we initialize Sentry SDK. This is useful for error tracking and performance monitoring. See https://docs.sentry.io/platforms/python/guides/fastapi/ for more information on how to configure Sentry with FastAPI.")  # fmt: off
    send_default_pii: bool = Field(default=True, description="See https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info.")  # fmt: off
    traces_sample_rate: float = Field(default=1.0, description="Set traces_sample_rate to 1.0 to capture 100% of transactions for tracing.")  # fmt: off
    profile_session_sample_rate: float = Field(default=1.0, description="Set profile_session_sample_rate to 1.0 to profile 100% of profile sessions.")  # fmt: off
    profile_lifecycle: str = Field(default="trace", description="Set profile_lifecycle to 'trace' to automatically run the profiler on when there is an active transaction.")  # fmt: off


class MonitoringPrometheus(ConfigBaseModel):
    enabled: bool = True


class MonitoringPostgres(ConfigBaseModel):
    enabled: bool = True


class MonitoringSentry(ConfigBaseModel):
    enabled: bool = True
    args: MonitoringSentryArgs


class Monitoring(ConfigBaseModel):
    prometheus: Optional[MonitoringPrometheus] = None
    postgres: Optional[MonitoringPostgres] = None
    sentry: Optional[MonitoringSentry] = None


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

    # Others
    disabled_routers: List[Literal[*ROUTERS]] = []
    tokenizer: LimitsTokenizer = LimitsTokenizer.TIKTOKEN_O200K_BASE
    metrics_retention_ms: int = 40_000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class MCP(ConfigBaseModel):
    mcp_bridge_url: str = "changeme"


class Config(ConfigBaseModel):
    general: General = Field(default_factory=General)
    auth: Auth = Field(default_factory=Auth)
    models: List[Model] = Field(min_length=1)
    databases: List[Database] = Field(min_length=2)
    multi_agents_search: Optional[MultiAgentsSearch] = None
    mcp: MCP = Field(default_factory=MCP)
    parser: Optional[Parser] = None
    web_search: Optional[WebSearch] = Field(default=None, description="Web search feature. Pre-requisite: vector database and text-generation or image-text-to-text model.")  # fmt: off
    monitoring: Monitoring = Field(default_factory=Monitoring)

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
        assert len(redis_databases) == 1, "There must be only one redis database."

        qdrant_databases = [database for database in values.databases if database.type == DatabaseType.QDRANT]
        assert len(qdrant_databases) <= 1, "There must not more than one database."

        elasticsearch_databases = [database for database in values.databases if database.type == DatabaseType.ELASTICSEARCH]
        assert len(elasticsearch_databases) <= 1, "There must not more than one database."

        assert elasticsearch_databases == [] or qdrant_databases == [], "Only one vector database (Qdrant or Elasticsearch) is allowed."  # fmt: off

        sql_databases = [database for database in values.databases if database.type == DatabaseType.SQL and database.context == "api"]
        if len(sql_databases) > 1:
            raise ValueError("There must be only one SQL database with the `api` context. If your configuration files contains multiple SQL databases, please specify the context keyword for other SQL databases.")  # fmt: off
        if len(sql_databases) == 0:
            raise ValueError("There must be at least one SQL database.")

        values.databases = SimpleNamespace()
        values.databases.redis = redis_databases[0] if redis_databases else None
        values.databases.sql = sql_databases[0] if sql_databases else None

        # vector store
        if qdrant_databases:
            values.databases.vector_store = qdrant_databases[0]
        elif elasticsearch_databases:
            values.databases.vector_store = elasticsearch_databases[0]
        else:
            values.databases.vector_store = None

        return values


class Settings(BaseSettings):
    model_config = ConfigDict(extra="allow")

    # config
    config_file: str = "config.yml"

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
        for match in set(re.findall(pattern=r"\${[A-Z0-9_]*}", string=file_content)):
            variable = match.replace("${", "").replace("}", "")
            if os.getenv(variable) is None or os.getenv(variable) == "":
                logging.warning(f"Environment variable {variable} not found or empty to replace {match}.")
            file_content = file_content.replace(match, os.getenv(variable, match))

        config = Config(**yaml.safe_load(file_content))

        values.general = config.general
        values.auth = config.auth
        values.web_search = config.web_search
        values.models = config.models
        values.monitoring = config.monitoring
        values.databases = config.databases
        values.multi_agents_search = config.multi_agents_search
        values.mcp = config.mcp
        values.parser = config.parser

        if values.databases.vector_store:
            assert values.databases.sql, "SQL database is required to use vector store features."
            assert values.databases.vector_store.model in [model.id for model in values.models if model.type == ModelType.TEXT_EMBEDDINGS_INFERENCE], f"Vector store model is not defined in models section with type {ModelType.TEXT_EMBEDDINGS_INFERENCE}."  # fmt: off

        if values.web_search:
            assert values.databases.vector_store, "Vector store database is required to use web_search."
            assert values.web_search.query_model in [model.id for model in values.models if model.type in [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT]], f"Web search model is not defined in models section with type {ModelType.TEXT_GENERATION}."  # fmt: off

        if values.multi_agents_search:
            assert values.databases.vector_store, "Vector store database is required to use multi-agents search."
            assert values.multi_agents_search.model in [model.id for model in values.models if model.type == ModelType.TEXT_GENERATION], f"Multi-agents search model is not defined in models section with type {ModelType.TEXT_GENERATION}."  # fmt: off

        return values
