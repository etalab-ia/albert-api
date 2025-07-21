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
from app.sql.session import get_db_session

from app.schemas.core.configuration import Model, ModelProvider


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

    dependencies = SimpleNamespace(mcp_bridge=mcp_bridge, parser=parser, redis=redis, vector_store=vector_store, web_search_engine=web_search_engine, model_database_manager=model_database_manager)

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


async def _setup_model_registry(configuration: Configuration, global_context: GlobalContext, dependencies: SimpleNamespace):

    db_routers = []

    async for session in get_db_session():
        db_routers = await dependencies.model_database_manager.get_routers(session=session, configuration=configuration, dependencies=dependencies)
    
    db_routers_from_config = [router for router in db_routers if router.from_config == True]

    if db_routers:

        for router in configuration.models:
            # @TODO show diff, log when adding model

            # The check will be different, see how it works 
            assert router in db_routers_from_config, f"Incoherent data between config and DB for router {router.name}"
            logger.info(msg=f"model {router.name} from config is coherent with DB data.")

        for router in db_routers:
            logger.info(msg=f"add model {router.name} from DB.")

        routers = db_routers
    else:
        logger.warning(msg="no ModelRouters found in database. Populating DB from configuration file.")
        routers = configuration.models

        for router in routers:
            async for session in get_db_session():
                # change input router to be a ModelRouterSchema
                await dependencies.model_database_manager.add_router(session=session, router=router)
    
    # Somehow convert the List of ModelRouterSchema to a List of ModelRouter

    global_context.model_registry = ModelRegistry(routers=routers)


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
