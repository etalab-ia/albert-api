from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from redis.asyncio.connection import ConnectionPool
from slowapi import Limiter
from slowapi.util import get_ipaddr

from app.clients import AuthenticationClient, CacheClient
from app.clients.internet import BaseInternetClient as InternetClient
from app.clients.search import BaseSearchClient as SearchClient
from app.helpers import ModelRegistry
from app.utils.settings import settings

clients = SimpleNamespace()

limiter = Limiter(
    key_func=get_ipaddr,
    storage_uri=f"redis://{settings.databases.redis.args.get("username", "")}:{settings.databases.redis.args.get("password", "")}@{settings.databases.redis.args.get("host", "localhost")}:{settings.databases.redis.args.get("port", 6379)}",
    default_limits=[settings.rate_limit.by_ip],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    app.state.limiter = limiter

    clients.models = ModelRegistry(settings=settings.models)
    clients.cache = CacheClient(connection_pool=ConnectionPool(**settings.databases.redis.args))
    clients.internet = InternetClient.import_constructor(type=settings.internet.type)(**settings.internet.args)
    clients.auth = AuthenticationClient(cache=clients.cache, **settings.databases.grist.args) if settings.databases.grist else None

    type = settings.databases.qdrant.type if settings.databases.qdrant else settings.databases.elastic.type
    args = settings.databases.qdrant.args if settings.databases.qdrant else settings.databases.elastic.args
    clients.search = SearchClient.import_constructor(type=type)(models=clients.models, **args)

    yield

    clients.search.close()
