from contextlib import asynccontextmanager
import logging
import traceback
from types import SimpleNamespace

from coredis import ConnectionPool
from fastapi import FastAPI

from app.clients.database import QdrantClient
from app.clients.model import BaseModelClient as ModelClient
from app.clients.web_search import BaseWebSearchClient as WebSearchClient
from app.helpers import DocumentManager, IdentityAccessManager, Limiter, ModelRegistry, ModelRouter, WebSearchManager
from app.utils.settings import settings

logger = logging.getLogger(__name__)
context = SimpleNamespace(models=None, iam=None, limiter=None, documents=None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    # setup clients
    qdrant = QdrantClient(**settings.databases.qdrant.args) if settings.databases.qdrant else None

    redis = ConnectionPool(**settings.databases.redis.args) if settings.databases.redis else None
    web_search = WebSearchClient.import_module(type=settings.web_search.type)(**settings.web_search.args) if settings.web_search else None
    routers = []
    for model in settings.models:
        clients = []
        for client in model.clients:
            try:
                # model client can be not reatachable to API start up
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

        logger.info(msg=f"add model {model.id} ({len(clients)}/{len(model.clients)} clients).")
        model = model.model_dump()
        model["clients"] = clients
        routers.append(ModelRouter(**model))

    # setup context: models, iam, limiter
    context.models = ModelRegistry(routers=routers)
    context.iam = IdentityAccessManager()
    context.limiter = Limiter(connection_pool=redis, strategy=settings.auth.limiting_strategy) if redis else None

    if redis:
        assert await context.limiter.redis.check(), "Redis database is not reachable."

    # setup context: documents
    web_search = WebSearchManager(web_search=web_search) if settings.web_search else None
    web_search_model = context.models(model=settings.web_search.model) if web_search else None
    qdrant_model = context.models(model=settings.databases.qdrant.model) if qdrant else None
    context.documents = DocumentManager(qdrant=qdrant, qdrant_model=qdrant_model, web_search=web_search, web_search_model=web_search_model) if qdrant else None  # fmt: off

    if qdrant:
        assert await context.documents.qdrant.check(), "Qdrant database is not reachable."

    yield

    # cleanup resources when app shuts down
    await qdrant.close()
