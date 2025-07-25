from contextlib import asynccontextmanager
import traceback
from types import SimpleNamespace

from coredis import ConnectionPool, Redis
from fastapi import FastAPI

from app.clients.mcp_bridge import BaseMCPBridgeClient as MCPBridgeClient
from app.clients.model import BaseModelClient as ModelClient
from app.clients.parser import BaseParserClient as ParserClient
from app.clients.vector_store import BaseVectorStoreClient as VectorStoreClient
from app.clients.web_search_engine import BaseWebSearchEngineClient as WebSearchEngineClient
from app.helpers._agentmanager import AgentManager
from app.helpers._documentmanager import DocumentManager
from app.helpers._identityaccessmanager import IdentityAccessManager
from app.helpers._limiter import Limiter
from app.helpers._multiagentmanager import MultiAgentManager
from app.helpers._parsermanager import ParserManager
from app.helpers._usagetokenizer import UsageTokenizer
from app.helpers._websearchmanager import WebSearchManager
from app.helpers._modeldatabasemanager import ModelDatabaseManager
from app.helpers.models import ModelRegistry
from app.helpers.models.routers import ModelRouter
from app.schemas.core.configuration import Configuration
from app.schemas.core.context import GlobalContext
from app.utils.configuration import get_configuration
from app.utils.context import global_context
from app.utils.logging import init_logger
from app.utils.rabbitmq import AsyncRabbitMQConnection
from app.sql.session import get_db_session

from app.schemas.core.configuration import Model as ModelRouterSchema


logger = init_logger(name=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    configuration = get_configuration()

    # Dependencies
    mcp_bridge = MCPBridgeClient.import_module(type=configuration.dependencies.mcp_bridge.type)(**configuration.dependencies.mcp_bridge.model_dump()) if configuration.dependencies.mcp_bridge else None  # fmt: off
    parser = ParserClient.import_module(type=configuration.dependencies.parser.type)(**configuration.dependencies.parser.model_dump()) if configuration.dependencies.parser else None  # fmt: off
    redis = ConnectionPool(**configuration.dependencies.redis.model_dump())
    vector_store = VectorStoreClient.import_module(type=configuration.dependencies.vector_store.type)(**configuration.dependencies.vector_store.model_dump()) if configuration.dependencies.vector_store else None  # fmt: off
    web_search_engine = WebSearchEngineClient.import_module(type=configuration.dependencies.web_search_engine.type)(**configuration.dependencies.web_search_engine.model_dump()) if configuration.dependencies.web_search_engine else None  # fmt: off
    model_database_manager = ModelDatabaseManager()

    redis_test_client = Redis(connection_pool=redis)
    assert (await redis_test_client.ping()).decode("ascii") == "PONG", "Redis database is not reachable."
    assert await vector_store.check() if vector_store else True, "Vector store database is not reachable."

    dependencies = SimpleNamespace(
        mcp_bridge=mcp_bridge,
        parser=parser,
        redis=redis,
        vector_store=vector_store,
        web_search_engine=web_search_engine,
        model_database_manager=model_database_manager,
    )

    if configuration.dependencies.rabbitmq:
        await AsyncRabbitMQConnection().setup()

    # setup global context
    await _setup_model_registry(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_identity_access_manager(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_limiter(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_tokenizer(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_agent_manager(configuration=configuration, global_context=global_context, dependencies=dependencies)
    await _setup_document_manager(configuration=configuration, global_context=global_context, dependencies=dependencies)

    yield

    # cleanup resources when app shuts down
    if vector_store:
        await vector_store.close()

    if configuration.dependencies.rabbitmq:

        logger.info("RabbitMQ: shutting down consumers and deleting existing queues.")
        for router in (await global_context.model_registry.get_router_instances()):
            await router.rabbitmq_shutdown()

        logger.info("RabbitMQ: closing connection.")
        await AsyncRabbitMQConnection().close()


async def _setup_model_registry(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    """
    Sets up the model registry by fetching the models defined in the database and the configuration file.
    Basic conflict handling between the database and the config.yml.
    """

    db_models = []

    async for session in get_db_session():
        db_models = await dependencies.model_database_manager.get_routers(session=session)

    if not db_models:
        logger.warning(msg="no ModelRouters found in database.")


    db_names = {model.name for model in db_models}
    config_names = {model.name for model in configuration.models}

    assert not db_names & config_names, f"found duplicate model names {', '.join(db_names & config_names)}"

    models = configuration.models + db_models

    routers = [await _convert_modelrouterschema_to_modelrouter(configuration=configuration, router=router, dependencies=dependencies) for router in models]
    
    global_context.model_registry = ModelRegistry(routers=routers)


async def _convert_modelrouterschema_to_modelrouter(configuration: Configuration, router: ModelRouterSchema, dependencies: SimpleNamespace):
    """
    Handles the conversion from the pydantic schema to the object ModelRouter.
    """

    providers = []
    for provider in router.providers:
        try:
            # model provider can be not reachable to API start up
            provider = ModelClient.import_module(type=provider.type)(
                redis=dependencies.redis,
                metrics_retention_ms=configuration.settings.metrics_retention_ms,
                **provider.model_dump(),
            )
            providers.append(provider)
        except Exception:
            logger.debug(msg=traceback.format_exc())
            continue
    if not providers:
        logger.error(msg=f"skip model {router.name} (0/{len(router.providers)} providers).")

        # check if models specified in configuration are reachable
        if configuration.settings.search_web_query_model and router.name == configuration.settings.search_web_query_model:
            raise ValueError(f"Query web search model ({router.name}) must be reachable.")
        if configuration.settings.vector_store_model and router.name == configuration.settings.vector_store_model:
            raise ValueError(f"Vector store embedding model ({router.name}) must be reachable.")
        if router.name == configuration.settings.search_multi_agents_synthesis_model:
            raise ValueError(f"Multi agents synthesis model ({router.name}) must be reachable.")
        if router.name == configuration.settings.search_multi_agents_reranker_model:
            raise ValueError(f"Multi agents reranker model ({router.name}) must be reachable.")

    logger.info(msg=f"add model {router.name} ({len(providers)}/{len(router.providers)} providers).")
    router = router.model_dump()
    router["providers"] = providers

    return ModelRouter(**router)


async def _setup_identity_access_manager(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    global_context.identity_access_manager = IdentityAccessManager(
        master_key=configuration.settings.auth_master_key,
        max_token_expiration_days=configuration.settings.auth_max_token_expiration_days,
    )


async def _setup_limiter(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    limiter = Limiter(redis=dependencies.redis, strategy=configuration.settings.rate_limiting_strategy)

    global_context.limiter = limiter


async def _setup_tokenizer(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    global_context.tokenizer = UsageTokenizer(tokenizer=configuration.settings.usage_tokenizer)


async def _setup_agent_manager(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    assert global_context.model_registry, "Set model registry in global context before setting up agent manager."
    global_context.agent_manager = AgentManager(
        mcp_bridge=dependencies.mcp_bridge,
        model_registry=global_context.model_registry,
        max_iterations=configuration.settings.mcp_max_iterations,
    )


async def _setup_document_manager(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):
    assert global_context.model_registry, "Set model registry in global context before setting up document manager."

    web_search_manager, parser_manager, multi_agent_manager = None, None, None

    if dependencies.vector_store is None:
        global_context.document_manager = None
        return

    if dependencies.web_search_engine:
        web_search_manager = WebSearchManager(
            web_search_engine=dependencies.web_search_engine,
            query_model=await global_context.model_registry(model=configuration.settings.search_web_query_model),
            limited_domains=configuration.settings.search_web_limited_domains,
            user_agent=configuration.settings.search_web_user_agent,
        )

    if dependencies.parser:
        parser_manager = ParserManager(parser=dependencies.parser)

    if configuration.settings.search_multi_agents_synthesis_model:
        multi_agent_manager = MultiAgentManager(
            synthesis_model=await global_context.model_registry(model=configuration.settings.search_multi_agents_synthesis_model),
            reranker_model=await global_context.model_registry(model=configuration.settings.search_multi_agents_reranker_model),
        )

    global_context.document_manager = DocumentManager(
        vector_store=dependencies.vector_store,
        vector_store_model=await global_context.model_registry(model=configuration.settings.vector_store_model),
        parser_manager=parser_manager,
        web_search_manager=web_search_manager,
        multi_agent_manager=multi_agent_manager,
    )
