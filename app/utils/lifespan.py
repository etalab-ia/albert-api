from contextlib import asynccontextmanager
import traceback

from coredis import ConnectionPool
from fastapi import FastAPI

from app.clients.database import QdrantClient
from app.clients.mcp import SecretShellMCPBridgeClient
from app.clients.model import BaseModelClient as ModelClient
from app.clients.parser import BaseParserClient as ParserClient
from app.clients.web_search import BaseWebSearchClient as WebSearchClient
from app.helpers._documentmanager import DocumentManager
from app.helpers._identityaccessmanager import IdentityAccessManager
from app.helpers._limiter import Limiter
from app.helpers._usagetokenizer import UsageTokenizer
from app.helpers._websearchmanager import WebSearchManager
from app.helpers.agents import AgentsManager
from app.helpers.models import ModelRegistry
from app.helpers.models.routers import ModelRouter
from app.utils import multiagents
from app.utils.context import global_context
from app.utils.logging import init_logger
from app.utils.settings import settings

logger = init_logger(name=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    # setup clients
    mcp_bridge = SecretShellMCPBridgeClient("http://localhost:9876")

    redis = ConnectionPool(**settings.databases.redis.args) if settings.databases.redis else None
    web_search = (
        WebSearchClient.import_module(type=settings.web_search.type)(user_agent=settings.web_search.user_agent, **settings.web_search.args)
        if settings.web_search
        else None
    )
    routers = []
    for model in settings.models:
        clients = []
        for client in model.clients:
            try:
                # model client can be not reatachable to API start up
                client = ModelClient.import_module(type=client.type)(
                    model=client.model,
                    costs=client.costs,
                    carbon=client.carbon,
                    **client.args.model_dump(),
                )
                clients.append(client)
            except Exception as e:
                logger.debug(msg=traceback.format_exc())
                continue
        if not clients:
            logger.error(msg=f"skip model {model.id} (0/{len(model.clients)} clients).")
            if settings.web_search:
                assert model.id != settings.web_search.model, f"Web search model ({model.id}) must be reachable."
            if settings.databases.qdrant:
                assert model.id != settings.databases.qdrant.model, f"Qdrant model ({model.id}) must be reachable."
            continue

        logger.info(msg=f"add model {model.id} ({len(clients)}/{len(model.clients)} clients).")
        model = model.model_dump()
        model["clients"] = clients
        routers.append(ModelRouter(**model))

    redis = ConnectionPool(**settings.databases.redis.args) if settings.databases.redis else None
    # TODO: pass user_agent in args
    web_search = WebSearchClient.import_module(type=settings.web_search.type)(user_agent=settings.web_search.user_agent, **settings.web_search.args) if settings.web_search else None  # fmt: off
    parser = ParserClient.import_module(type=settings.parser.type)(**settings.parser.args.model_dump()) if settings.parser else None
    qdrant = QdrantClient(**settings.databases.qdrant.args) if settings.databases.qdrant else None

    # setup context: models, iam, limiter, tokenizer
    global_context.tokenizer = UsageTokenizer(tokenizer=settings.general.tokenizer)
    global_context.models = ModelRegistry(routers=routers)
    global_context.iam = IdentityAccessManager()
    global_context.limiter = Limiter(connection_pool=redis, strategy=settings.auth.limiting_strategy) if redis else None

    qdrant = QdrantClient(**settings.databases.qdrant.args) if settings.databases.qdrant else None
    qdrant.model = global_context.models(model=settings.databases.qdrant.model) if qdrant else None

    global_context.parser = ParserManager(parser=parser)
    mcp_bridge = SecretShellMCPBridgeClient(settings.mcp.mcp_bridge_url)
    global_context.mcp.agents_manager = AgentsManager(mcp_bridge, global_context.models)
    if redis:
        assert await global_context.limiter.redis.check(), "Redis database is not reachable."

    # setup context: documents
    qdrant.model = global_context.models(model=settings.databases.qdrant.model) if qdrant else None

    # TODO: pass domains in websearchmanager arguments
    web_search = WebSearchManager(web_search=web_search, model=global_context.models(model=settings.web_search.model)) if settings.web_search else None  # fmt: off

    # @TODO: refacto import of multiagents into DocumentManager
    multi_agents_search_model = global_context.models(model=settings.multi_agents_search.model) if settings.multi_agents_search else None
    multiagents.MultiAgents.model = global_context.models(model=settings.multi_agents_search.model) if settings.multi_agents_search else None
    multiagents.MultiAgents.ranker_model = global_context.models(model=settings.multi_agents_search.ranker_model) if settings.multi_agents_search else None  # fmt: off

    global_context.documents = DocumentManager(qdrant=qdrant, web_search=web_search, multi_agents_search_model=multi_agents_search_model) if qdrant else None  # fmt: off

    # check databases are reachable
    if redis:
        assert await global_context.limiter.redis.check(), "Redis database is not reachable."

    if qdrant:
        assert await global_context.documents.qdrant.check(), "Qdrant database is not reachable."

    yield

    # cleanup resources when app shuts down
    await qdrant.close()
