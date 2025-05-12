from contextlib import asynccontextmanager
import traceback

from coredis import ConnectionPool
from fastapi import FastAPI

from app.clients.database import QdrantClient
from app.clients.model import BaseModelClient as ModelClient
from app.clients.web_search import BaseWebSearchClient as WebSearchClient
from app.helpers import DocumentManager, IdentityAccessManager, Limiter, WebSearchManager, UsageTokenizer
from app.helpers.models import ModelRegistry
from app.helpers.models.routers import ImmediateModelRouter, QueuingModelRouter
from app.helpers.message_producer.rpc_client import RPCClient
from app.schemas.core.models import RoutingMode
from app.utils import multiagents
from app.utils.logging import init_logger
from app.utils.settings import settings
from app.utils.context import global_context

logger = init_logger(name=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    # setup clients
    redis = ConnectionPool(**settings.databases.redis.args) if settings.databases.redis else None
    web_search = (
        WebSearchClient.import_module(type=settings.web_search.type)(user_agent=settings.web_search.user_agent, **settings.web_search.args)
        if settings.web_search
        else None
    )
    routers = []
    message_producer = None
    for model in settings.models:
        clients = []
        for client in model.clients:
            try:
                # model client can be not reachable to API start up
                client = ModelClient.import_module(type=client.type)(model=client.model, **client.args.model_dump())
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

        queuing_enabled = model.routing_mode == RoutingMode.QUEUEING
        log_message = f"add model {model.id} ({len(clients)}/{len(model.clients)} clients)"
        model = model.model_dump()
        model["clients"] = clients

        if queuing_enabled:
            if message_producer is None:
                message_producer = RPCClient()
            routers.append(QueuingModelRouter(message_producer, **model))
            log_message = f"{log_message}, with queuing enabled."
        else:
            routers.append(ImmediateModelRouter(**model))
            log_message = f"{log_message}."

        logger.info(msg=log_message)

    # setup context: models, iam, limiter, tokenizer
    global_context.tokenizer = UsageTokenizer(tokenizer=settings.usages.tokenizer)
    global_context.models = ModelRegistry(routers=routers)
    global_context.iam = IdentityAccessManager()
    global_context.limiter = Limiter(connection_pool=redis, strategy=settings.auth.limiting_strategy) if redis else None

    qdrant = QdrantClient(**settings.databases.qdrant.args) if settings.databases.qdrant else None
    qdrant.model = global_context.models(model=settings.databases.qdrant.model) if qdrant else None

    if redis:
        assert await global_context.limiter.redis.check(), "Redis database is not reachable."

    # setup context: documents
    web_search = (
        WebSearchManager(web_search=web_search, model=global_context.models(model=settings.web_search.model)) if settings.web_search else None
    )
    multi_agents_search_model = global_context.models(model=settings.multi_agents_search.model) if settings.multi_agents_search else None
    global_context.documents = DocumentManager(qdrant=qdrant, web_search=web_search, multi_agents_search_model=multi_agents_search_model) if qdrant else None  # fmt: off

    multiagents.MultiAgents.model = global_context.models(model=settings.multi_agents_search.model) if settings.multi_agents_search else None
    multiagents.MultiAgents.ranker_model = global_context.models(model=settings.multi_agents_search.ranker_model) if settings.multi_agents_search else None  # fmt: off

    if qdrant:
        assert await global_context.documents.qdrant.check(), "Qdrant database is not reachable."

    yield

    # cleanup resources when app shuts down
    await qdrant.close()
