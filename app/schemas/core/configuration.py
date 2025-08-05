from enum import Enum
from functools import wraps
import logging
import os
import re
from typing import Any, Dict, List, Literal, Optional, Type

import pycountry
from pydantic import BaseModel, ConfigDict, Field, constr, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings
import yaml

from app.schemas.models import ModelType
from app.utils.variables import DEFAULT_APP_NAME, DEFAULT_TIMEOUT, ROUTERS

# utils ----------------------------------------------------------------------------------------------------------------------------------------------


def custom_validation_error(url: Optional[str] = None):
    """
    Decorator to override Pydantic ValidationError to change error message.

    Args:
        url(Optional[str]): override Pydantic documentation URL by provided URL. If not provided, the error message will be the same as the original error message.
    """

    class ValidationError(Exception):
        def __init__(self, exc: PydanticValidationError, cls: BaseModel, url: str):
            super().__init__()
            error_count = exc.error_count()
            error_content = exc.errors()
            message = f"{error_count} validation error for {cls.__name__}\n"

            for error in error_content:
                url = url or error["url"]
                if error["type"] == "assertion_error":
                    message += f"{error["msg"]}\n"
                else:
                    if len(error["loc"]) > 0:
                        message += f"{error["loc"][0]}\n"
                    message += f"  {error["msg"]} [type={error["type"]}, input_value={error.get("input", "")}, input_type={type(error.get("input")).__name__}]\n"  # fmt: off
                    if len(error["loc"]) > 0:
                        description = cls.__pydantic_fields__[error["loc"][0]].description
                        if description:
                            message += f"\n  {description}\n"
                message += f"    For further information visit {url}\n\n"

            self.message = message

        def __str__(self):
            return self.message

    def decorator(cls: Type[BaseModel]):
        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, **data):
            try:
                original_init(self, **data)
            except PydanticValidationError as e:
                raise ValidationError(exc=e, cls=cls, url=url) from None  # hide previous traceback

        cls.__init__ = new_init
        return cls

    return decorator


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


# models ---------------------------------------------------------------------------------------------------------------------------------------------


class ModelProviderType(str, Enum):
    ALBERT = "albert"
    OPENAI = "openai"
    TEI = "tei"
    VLLM = "vllm"

    @classmethod
    def get_supported_clients(cls, model_type):
        mapping = {
            ModelType.AUTOMATIC_SPEECH_RECOGNITION: [cls.ALBERT.value, cls.OPENAI.value],
            ModelType.IMAGE_TEXT_TO_TEXT: [cls.ALBERT.value, cls.OPENAI.value, cls.VLLM.value],
            ModelType.TEXT_EMBEDDINGS_INFERENCE: [cls.ALBERT.value, cls.OPENAI.value, cls.TEI.value],
            ModelType.TEXT_GENERATION: [cls.ALBERT.value, cls.OPENAI.value, cls.VLLM.value],
            ModelType.TEXT_CLASSIFICATION: [cls.ALBERT.value, cls.TEI.value],
        }
        return mapping.get(model_type, [])


class RoutingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    SHUFFLE = "shuffle"


CountryCodes = [country.alpha_3 for country in pycountry.countries]
CountryCodes.append("WOR")  # Add world as a country code, default value of the carbon footprint computation framework
CountryCodes = {str(lang).upper(): str(lang) for lang in sorted(set(CountryCodes))}
CountryCodes = Enum("CountryCodes", CountryCodes, type=str)


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#modelprovider")
class ModelProvider(ConfigBaseModel):
    type: ModelProviderType = Field(required=True, description="Model provider type.", examples=["openai"])  # fmt: off
    url: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, required=False, description="Model provider API url. The url must only contain the domain name (without `/v1` suffix for example). Depends of the model provider type, the url can be optional (Albert, OpenAI).", examples=["https://api.openai.com"])  # fmt: off
    key: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, required=False, description="Model provider API key.", examples=["sk-1234567890"])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, required=False, description="Timeout for the model provider requests, after user receive an 500 error (model is too busy).", examples=[10])  # fmt: off
    model_name: constr(strip_whitespace=True, min_length=1) = Field(required=True, description="Model name from the model provider.", examples=["gpt-4o"])  # fmt: off
    model_cost_prompt_tokens: float = Field(default=0.0, required=False, ge=0.0, description="Model costs prompt tokens for user budget computation. The cost is by 1M tokens.", examples=[0.1])  # fmt: off
    model_cost_completion_tokens: float = Field(default=0.0, required=False, ge=0.0, description="Model costs completion tokens for user budget computation. The cost is by 1M tokens.", examples=[0.1])  # fmt: off
    model_carbon_footprint_zone: CountryCodes = Field(default=CountryCodes.WOR, required=False, description="Model hosting zone for carbon footprint computation (with ISO 3166-1 alpha-3 code format). For more information, see https://ecologits.ai", examples=["WOR"])  # fmt: off
    model_carbon_footprint_total_params: Optional[float] = Field(default=None, required=False, ge=0.0, description="Total params of the model in billions of parameters for carbon footprint computation. If not provided, the active params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai", examples=[8])  # fmt: off
    model_carbon_footprint_active_params: Optional[float] = Field(default=None, required=False, ge=0.0, description="Active params of the model in billions of parameters for carbon footprint computation. If not provided, the total params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai", examples=[8])  # fmt: off

    @model_validator(mode="after")
    def complete_values(cls, values):
        # complete url
        if values.url is None:
            if values.type == ModelProviderType.OPENAI:
                values.url = "https://api.openai.com"
            elif values.type == ModelProviderType.ALBERT:
                values.url = "https://albert.api.etalab.gouv.fr"
            else:
                raise ValueError(f"URL is required for {values.type.value} model provider type.")

        # complete model_cost_prompt_tokens and model_cost_completion_tokens
        if values.model_cost_prompt_tokens is None and values.model_cost_completion_tokens is not None:
            values.model_cost_prompt_tokens = values.model_cost_completion_tokens

        if values.model_carbon_footprint_total_params is None and values.model_carbon_footprint_active_params is not None:
            values.model_carbon_footprint_total_params = values.model_carbon_footprint_active_params
        if values.model_carbon_footprint_active_params is None and values.model_carbon_footprint_total_params is not None:
            values.model_carbon_footprint_active_params = values.model_carbon_footprint_total_params

        return values


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#model")
class Model(ConfigBaseModel):
    """
    In the models section, you define a list of models. Each model is a set of API providers for that model. Users will access the models specified in
    this section using their *name*. Load balancing is performed between the different providers of the requested model. All providers in a model must
    serve the same type of model (text-generation or text-embeddings-inference, etc.). We recommend that all providers of a model serve exactly the same
    model, otherwise users may receive responses of varying quality. For embedding models, the API verifies that all providers output vectors of the
    same dimension. You can define the load balancing strategy between the model's providers. By default, it is random.

    For more information to configure model providers, see the [ModelProvider section](#modelprovider).
    """

    type: ModelType = Field(required=True, description="Type of the model. It will be used to identify the model type.", examples=["text-generation"])  # fmt: off
    aliases: List[constr(strip_whitespace=True, min_length=1, max_length=64)] = Field(default_factory=list, required=False, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])  # fmt: off
    owned_by: constr(strip_whitespace=True, min_length=1, max_length=64) = Field(default=DEFAULT_APP_NAME, required=False, description="Owner of the model displayed in `/v1/models` endpoint.", examples=["my-app"])  # fmt: off
    routing_strategy: RoutingStrategy = Field(default=RoutingStrategy.SHUFFLE, required=False, description="Routing strategy for load balancing between providers of the model. It will be used to identify the model type.", examples=["round_robin"])  # fmt: off
    providers: List[ModelProvider] = Field(required=True, description="API providers of the model. If there are multiple providers, the model will be load balanced between them according to the routing strategy. The different models have to the same type.")  # fmt: off

    @model_validator(mode="after")
    def validate_model_type(cls, values):
        for provider in values.providers:
            assert provider.type.value in ModelProviderType.get_supported_clients(values.type.value), f"Invalid model type: {values.type.value} for client type {provider.type.value}"  # fmt: off

        if values.type not in [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT]:
            for provider in values.providers:
                if provider.model_carbon_footprint_active_params is not None:
                    logging.warning(f"Carbon footprint is not supported for {values.type.value} models, set active params to None.")
                    provider.model_carbon_footprint_active_params = None
                if provider.model_carbon_footprint_total_params is not None:
                    logging.warning(f"Carbon footprint is not supported for {values.type.value} models, set total params to None.")
                    provider.model_carbon_footprint_total_params = None

        return values


# dependencies ---------------------------------------------------------------------------------------------------------------------------------------
class MCPBridgeType(str, Enum):
    SECRETIVESHELL = "secretiveshell"


class ParserType(str, Enum):
    ALBERT = "albert"
    MARKER = "marker"


class VectorStoreType(str, Enum):
    ELASTIC = "elasticsearch"
    QDRANT = "qdrant"


class WebSearchEngineType(str, Enum):
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"


class DependencyType(str, Enum):
    ALBERT = "albert"
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"
    ELASTIC = "elasticsearch"
    QDRANT = "qdrant"
    MARKER = "marker"
    POSTGRES = "postgres"
    REDIS = "redis"
    SECRETIVESHELL = "secretiveshell"
    SENTRY = "sentry"


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#albert")
class AlbertDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(default="https://albert.api.etalab.gouv.fr", required=False, description="Albert API url.")  # fmt: off
    headers: Dict[str, str] = Field(default_factory=dict, required=False, description="Albert API request headers.", examples=[{"Authorization": "Bearer my-api-key"}])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, required=False, description="Timeout for the Albert API requests.", examples=[10])  # fmt: off


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#brave")
class BraveDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(default="https://api.search.brave.com/res/v1/web/search", required=False, description="Brave API url.")  # fmt: off
    headers: Dict[str, str] = Field(default_factory=dict, required = True, description="Brave API request headers.", examples=[{"X-Subscription-Token": "my-api-key"}])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, required=False, description="Timeout for the Brave API requests.", examples=[10])  # fmt: off


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#duckduckgodependency")
class DuckDuckGoDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(default="https://api.duckduckgo.com/", required=False, description="DuckDuckGo API url.")  # fmt: off
    headers: Dict[str, str] = Field(default_factory=dict, required = False, description="DuckDuckGo API request headers.", examples=[{}])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, required=False, description="Timeout for the DuckDuckGo API requests.", examples=[10])  # fmt: off


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#elasticsearchdependency")
class ElasticsearchDependency(ConfigBaseModel):
    # All args of pydantic elastic client is allowed
    pass


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#qdrantdependency")
class QdrantDependency(ConfigBaseModel):
    # All args of pydantic qdrant client is allowed

    @model_validator(mode="after")
    def force_rest(cls, values):
        if hasattr(values, "prefer_grpc") and values.prefer_grpc:
            logging.warning(msg="Qdrant does not support grpc for create index payload, force REST connection.")
            values.prefer_grpc = False

        return values


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#markerdependency")
class MarkerDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(required=True, description="Marker API url.")  # fmt: off
    headers: Dict[str, str] = Field(default_factory=dict, required=False, description="Marker API request headers.", examples=[{"Authorization": "Bearer my-api-key"}])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, required=False, description="Timeout for the Marker API requests.", examples=[10])  # fmt: off


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#postgresdependency")
class PostgresDependency(ConfigBaseModel):
    # All args of pydantic postgres client is allowed
    url: constr(strip_whitespace=True, min_length=1) = Field(pattern=r"^postgresql", required=True, description="PostgreSQL connection url.")  # fmt: off

    @field_validator("url", mode="after")
    def force_async(cls, url):
        if url.startswith("postgresql://"):
            logging.warning(msg="PostgreSQL connection must be async, force asyncpg connection.")
            url = url.replace("postgresql://", "postgresql+asyncpg://")

        return url


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#secretiveshelldependency")
class SecretiveshellDependency(ConfigBaseModel):
    """
    See https://github.com/SecretiveShell/MCP-Bridge for more information.
    """

    url: constr(strip_whitespace=True, min_length=1) = Field(required=True, description="Secretiveshell API url.")  # fmt: off
    headers: Dict[str, str] = Field(default_factory=dict, required=False, description="Secretiveshell API request headers.")  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, required=False, description="Timeout for the Secretiveshell API requests.", examples=[10])  # fmt: off


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#sentrydependency")
class SentryDependency(ConfigBaseModel):
    pass
    # All args of pydantic sentry client is allowed


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#redisdependency")
class RedisDependency(ConfigBaseModel):
    pass
    # All args of pydantic redis client is allowed


class ProConnect(ConfigBaseModel):
    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    # OpenID Connect discovery endpoint for server metadata
    server_metadata_url: str = Field(default="https://identite-sandbox.proconnect.gouv.fr/.well-known/openid-configuration")
    redirect_uri: str = Field(default="https://albert.api.etalab.gouv.fr/v1/oauth2/callback")
    scope: str = Field(default="openid email given_name usual_name siret organizational_unit belonging_population chorusdt")
    allowed_domains: str = Field(default="localhost,gouv.fr", description="List of allowed domains for OAuth2 login. This is used to restrict the domains that can use the OAuth2 login flow.")  # fmt: off
    default_role: str = Field(default="Freemium", description="Default role assigned to users when they log in for the first time.")


@custom_validation_error(url="https://github.com/etalab-ia/albert-api/blob/main/docs/configuration.md#dependencies")
class Dependencies(ConfigBaseModel):
    albert: Optional[AlbertDependency] = Field(default=None, required=False, description="If provided, Albert API is used to parse pdf documents. Cannot be used with Marker dependency concurrently. Pass arguments to call Albert API in this section.")  # fmt: off
    brave: Optional[BraveDependency] = Field(default=None, required=False, description="If provided, Brave API is used to web search. Cannot be used with DuckDuckGo dependency concurrently. Pass arguments to call API in this section. All query parameters are supported, see https://api-dashboard.search.brave.com/app/documentation/web-search/query for more information.")  # fmt: off
    duckduckgo: Optional[DuckDuckGoDependency] = Field(default=None, required=False, description="If provided, DuckDuckGo API is used to web search. Cannot be used with Brave dependency concurrently. Pass arguments to call API in this section. All query parameters are supported, see https://www.searchapi.io/docs/duckduckgo-api for more information.")  # fmt: off
    elasticsearch: Optional[ElasticsearchDependency] = Field(default=None, required=False, description="Pass all elastic python SDK arguments, see https://elasticsearch-py.readthedocs.io/en/v9.0.2/api/elasticsearch.html#elasticsearch.Elasticsearch for more information.")  # fmt: off
    qdrant: Optional[QdrantDependency] = Field(default=None, required=False, description="Pass all qdrant python SDK arguments, see https://python-client.qdrant.tech/qdrant_client.qdrant_client for more information.")  # fmt: off
    marker: Optional[MarkerDependency] = Field(default=None, required=False, description="If provided, Marker API is used to parse pdf documents. Cannot be used with Albert dependency concurrently. Pass arguments to call Marker API in this section.")  # fmt: off
    postgres: PostgresDependency = Field(required=True, description="Pass all postgres python SDK arguments, see https://github.com/etalab-ia/opengatellm/blob/main/docs/dependencies/postgres.md for more information.")  # fmt: off
    # @TODO: support optional redis dependency with set redis in cache
    redis: RedisDependency  = Field(required=True, description="Pass all redis python SDK arguments, see https://redis.readthedocs.io/en/stable/connections.html for more information.")  # fmt: off
    secretiveshell: Optional[SecretiveshellDependency] = Field(default=None, required=False, description="If provided, MCP agents can use tools from SecretiveShell MCP Bridge. Pass arguments to call Secretiveshell API in this section, see https://github.com/SecretiveShell/MCP-Bridge for more information.")  # fmt: off
    sentry: Optional[SentryDependency] = Field(default=None, required=False, description="Pass all sentry python SDK arguments, see https://docs.sentry.io/platforms/python/configuration/options/ for more information.")  # fmt: off
    proconnect: ProConnect = Field(
        default_factory=ProConnect,
        required=False,
        description="ProConnect configuration for the API. See https://github.com/etalab-ia/albert-api/blob/main/docs/oauth2_encryption.md for more information.",
    )

    @model_validator(mode="after")
    def validate_dependencies(cls, values):
        def create_attribute(name: str, type: Enum, values: Any):
            candidates = [item for item in type if getattr(values, item.value) is not None]

            # Ensure only one dependency of this family is defined
            if len(candidates) > 1:
                raise ValueError(f"Only one {type.__name__} is allowed (provided: {", ".join(c.value for c in candidates)}).")

            # If no dependency is provided, set the attribute to None
            if len(candidates) == 0:
                setattr(values, name, None)
            else:
                chosen_enum = candidates[0]
                dep_obj = getattr(values, chosen_enum.value)

                # Add a `type` field on the dependency object to remember its family (string form)
                setattr(dep_obj, "type", chosen_enum)

                # Expose the dependency under the generic name (vector_store, parser, ...)
                setattr(values, name, dep_obj)

            # Clean up specific attributes
            for item in type:
                if hasattr(values, item.value):
                    delattr(values, item.value)

            return values

        values = create_attribute(name="web_search_engine", type=WebSearchEngineType, values=values)
        values = create_attribute(name="parser", type=ParserType, values=values)
        values = create_attribute(name="vector_store", type=VectorStoreType, values=values)
        values = create_attribute(name="mcp_bridge", type=MCPBridgeType, values=values)

        return values


# settings -------------------------------------------------------------------------------------------------------------------------------------------

Routers = {str(router).upper(): str(router) for router in sorted(ROUTERS)}
Routers = Enum("Routers", Routers, type=str)


class LimitingStrategy(str, Enum):
    MOVING_WINDOW = "moving_window"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class Tokenizer(str, Enum):
    TIKTOKEN_GPT2 = "tiktoken_gpt2"
    TIKTOKEN_R50K_BASE = "tiktoken_r50k_base"
    TIKTOKEN_P50K_BASE = "tiktoken_p50k_base"
    TIKTOKEN_P50K_EDIT = "tiktoken_p50k_edit"
    TIKTOKEN_CL100K_BASE = "tiktoken_cl100k_base"
    TIKTOKEN_O200K_BASE = "tiktoken_o200k_base"


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#settings")
class Settings(ConfigBaseModel):
    # other
    disabled_routers: List[Routers] = Field(default_factory=list, description="Disabled routers to limits services of the API.", examples=[["agents", "embeddings"]])  # fmt: off

    # metrics
    metrics_retention_ms: int = Field(default=40000, ge=1, description="Retention time for metrics in milliseconds.")  # fmt: off

    # usage tokenizer
    usage_tokenizer: Tokenizer = Field(default=Tokenizer.TIKTOKEN_GPT2, required=False, description="Tokenizer used to compute usage of the API.")  # fmt: off

    # logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", required=False, description="Logging level of the API.")  # fmt: off
    log_format: Optional[str] = Field(default="[%(asctime)s][%(process)d:%(name)s][%(levelname)s] %(client_ip)s - %(message)s", required=False, description="Logging format of the API.")  # fmt: off

    # swagger
    swagger_title: Optional[str] = Field(default="Albert API", description="Display title of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["Albert API"])  # fmt: off
    swagger_summary: Optional[str] = Field(default="Albert API connect to your models.", description="Display summary of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["Albert API connect to your models."])  # fmt: off
    swagger_version: Optional[str] = Field(default="latest", description="Display version of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["2.5.0"])  # fmt: off
    swagger_description: Optional[str] = Field(default="[See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md)", description="Display description of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["[See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md)"])  # fmt: off
    swagger_contact: Optional[Dict] = Field(default=None, description="Contact informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_license_info: Optional[Dict] = Field(default={"name": "MIT Licence", "identifier": "MIT", "url": "https://raw.githubusercontent.com/etalab-ia/opengatellm/refs/heads/main/LICENSE"}, description="Licence informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_terms_of_service: Optional[str] = Field(default=None, description="A URL to the Terms of Service for the API in swagger UI. If provided, this has to be a URL.", examples=["https://example.com/terms-of-service"])  # fmt: off
    swagger_openapi_tags: List[Dict[str, Any]] = Field(default_factory=list, description="OpenAPI tags of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_openapi_url: Optional[str] = Field(default="/openapi.json", pattern=r"^/", description="OpenAPI URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_docs_url: Optional[str] = Field(default="/docs", pattern=r"^/", description="Docs URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_redoc_url: Optional[str] = Field(default="/redoc", pattern=r"^/", description="Redoc URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off

    # mcp
    mcp_max_iterations: int = Field(default=2, ge=2, description="Maximum number of iterations for MCP agents in `/v1/agents/completions` endpoint.")  # fmt: off

    # auth
    auth_master_key: constr(strip_whitespace=True, min_length=1) = Field(default="changeme", required=False, description="Master key for the API. This key has all permissions and cannot be modified or deleted. This key is used to create the first role and the first user. This key is also used to encrypt user tokens, watch out if you modify the master key, you'll need to update all user API keys.")  # fmt: off
    auth_max_token_expiration_days: Optional[int] = Field(default=None, ge=1, description="Maximum number of days for a token to be valid.")  # fmt: off

    # rate_limiting
    rate_limiting_strategy: LimitingStrategy = Field(default=LimitingStrategy.FIXED_WINDOW, required=False, description="Rate limiting strategy for the API.")  # fmt: off

    # monitoring
    monitoring_postgres_enabled: bool = Field(default=True, required=False, description="If true, the log usage will be written in the PostgreSQL database.")  # fmt: off
    monitoring_prometheus_enabled: bool = Field(default=True, required=False, description="If true, Prometheus metrics will be exposed in the `/metrics` endpoint.")  # fmt: off

    # vector store
    vector_store_model: Optional[str] = Field(default=None, required=False, description="Model used to vectorize the text in the vector store database. Is required if a vector store dependency is provided (Elasticsearch or Qdrant). This model must be defined in the `models` section and have type `text-embeddings-inference`.")  # fmt: off

    # search - web
    search_web_query_model: Optional[str] = Field(default=None, required=False, description="Model used to query the web in the web search. Is required if a web search dependency is provided (Brave or DuckDuckGo). This model must be defined in the `models` section and have type `text-generation` or `image-text-to-text`.")  # fmt: off
    search_web_limited_domains: List[str] = Field(default_factory=list, description="Limited domains for the web search. If provided, the web search will be limited to these domains.")  # fmt: off
    search_web_user_agent: Optional[str] = Field(default=None, required=False, description="User agent to scrape the web. If provided, the web search will use this user agent.")  # fmt: off

    # search - multi agents
    search_multi_agents_synthesis_model: Optional[str] = Field(default=None, required=False, description="Model used to synthesize the results of multi-agents search. If not provided, multi-agents search is disabled. This model must be defined in the `models` section and have type `text-generation` or `image-text-to-text`.")  # fmt: off
    search_multi_agents_reranker_model: Optional[str] = Field(default=None, required=False, description="Model used to rerank the results of multi-agents search. If not provided, multi-agents search is disabled. This model must be defined in the `models` section and have type `text-generation` or `image-text-to-text`.")  # fmt: off

    session_secret_key: str = Field(description="Secret key for session middleware.")
    encryption_key: str = Field(description="Secret key for encrypting between FastAPI and Playground. Must be 32 url-safe base64-encoded bytes.")

    front_url: str = Field(default="http://localhost:8501", description="Front-end URL for the application.")


# load config ----------------------------------------------------------------------------------------------------------------------------------------


@custom_validation_error(url="https://github.com/etalab-ia/opengatellm/blob/main/docs/configuration.md#all-configuration")
class ConfigFile(ConfigBaseModel):
    """
    Refer to the [configuration example file](../../../config.example.yml) for an example of configuration.
    """

    models: List[Model] = Field(min_length=1, description="Models used by the API. At least one model must be defined.")  # fmt: off
    dependencies: Dependencies = Field(default_factory=Dependencies, description="Dependencies used by the API.")  # fmt: off
    settings: Settings = Field(default_factory=Settings, description="Settings used by the API.")  # fmt: off

    @model_validator(mode="after")
    def validate_models(cls, values) -> Any:
        # get all models and aliases for each model type
        models = {"all": []}
        for model_type in ModelType:
            models[model_type.value] = []
            for model in values.models:
                if model.type == model_type:
                    model_names_and_aliases = [alias for alias in model.aliases] + [model.name]
                    models[model_type.value].extend(model_names_and_aliases)

        # build the complete list of all models
        for model_type in ModelType:
            models["all"].extend(models[model_type.value])

        # check for duplicated name in models and aliases
        duplicated_models = [model for model in models["all"] if models["all"].count(model) > 1]
        if duplicated_models:
            raise ValueError(f"Duplicated model or alias names found: {", ".join(set(duplicated_models))}")

        # check for interdependencies
        if values.dependencies.vector_store:
            assert values.settings.vector_store_model, "Vector store model must be defined in settings section."
            assert values.settings.vector_store_model in models["all"], "Vector store model must be defined in models section."
            assert values.settings.vector_store_model in models[ModelType.TEXT_EMBEDDINGS_INFERENCE.value], f"The vector store model must have type {ModelType.TEXT_EMBEDDINGS_INFERENCE}."  # fmt: off

        if values.dependencies.web_search_engine:
            assert values.settings.search_web_query_model, "Web search query model must be defined in settings section."
            assert values.settings.search_web_query_model in models["all"], "Web search query model must be defined in models section."
            assert values.settings.search_web_query_model in models[ModelType.IMAGE_TEXT_TO_TEXT.value] + models[ModelType.TEXT_GENERATION.value], f"Web search query model must be defined in models section with type {ModelType.TEXT_GENERATION} or {ModelType.IMAGE_TEXT_TO_TEXT}."  # fmt: off

        if values.settings.search_multi_agents_synthesis_model:
            assert values.settings.search_multi_agents_synthesis_model in models["all"], "Multi-agents search synthesis model must be defined in models section."  # fmt: off
            assert values.settings.search_multi_agents_synthesis_model in models[ModelType.IMAGE_TEXT_TO_TEXT.value] + models[ModelType.TEXT_GENERATION.value], f"Multi-agents search synthesis model must have type {ModelType.IMAGE_TEXT_TO_TEXT} or {ModelType.TEXT_GENERATION}."  # fmt: off

            if values.settings.search_multi_agents_reranker_model is None:
                logging.warning("Multi-agents search reranker model is not defined, using multi-agents search synthesis model as reranker model.")
                values.settings.search_multi_agents_reranker_model = values.settings.search_multi_agents_synthesis_model

        if values.settings.search_multi_agents_reranker_model:
            assert values.settings.search_multi_agents_reranker_model in models["all"], "Multi-agents search reranker model must be defined in models section."  # fmt: off
            assert values.settings.search_multi_agents_reranker_model in models[ModelType.IMAGE_TEXT_TO_TEXT.value] + models[ModelType.TEXT_GENERATION.value], f"Multi-agents search reranker model must have type {ModelType.IMAGE_TEXT_TO_TEXT} or {ModelType.TEXT_GENERATION}."  # fmt: off

            if values.settings.search_multi_agents_synthesis_model is None:
                logging.warning("Multi-agents search synthesis model is not defined, using multi-agents search reranker model as synthesis model.")
                values.settings.search_multi_agents_synthesis_model = values.settings.search_multi_agents_reranker_model

        return values


class Configuration(BaseSettings):
    model_config = ConfigDict(extra="allow")

    # config
    config_file: str = "config.yml"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert os.path.exists(path=config_file), f"Config file ({config_file}) not found."
        return config_file

    @model_validator(mode="after")
    def setup_config(cls, values) -> Any:
        with open(file=values.config_file, mode="r") as file:
            lines = file.readlines()

        # remove commented lines
        uncommented_lines = [line for line in lines if not line.lstrip().startswith("#")]

        # replace environment variables
        file_content = cls.replace_environment_variables(file_content="".join(uncommented_lines))

        # load config
        config = ConfigFile(**yaml.safe_load(stream=file_content))

        values.models = config.models
        values.dependencies = config.dependencies
        values.settings = config.settings

        return values

    @classmethod
    def replace_environment_variables(cls, file_content):
        env_variable_pattern = re.compile(r"\${([A-Z0-9_]+)(:-[^}]*)?}")

        def replace_env_var(match):
            env_variable_definition = match.group(0)
            env_variable_name = match.group(1)
            default_env_variable_value = match.group(2)[2:] if match.group(2) else None

            env_variable_value = os.getenv(env_variable_name)

            if env_variable_value is not None and env_variable_value != "":
                return env_variable_value
            elif default_env_variable_value is not None:
                return default_env_variable_value
            else:
                logging.warning(f"Environment variable {env_variable_name} not found or empty to replace {env_variable_definition}.")
                return env_variable_definition

        file_content = env_variable_pattern.sub(replace_env_var, file_content)

        return file_content
