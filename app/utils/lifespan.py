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

models = SimpleNamespace()
databases = SimpleNamespace()
internet = SimpleNamespace()

limiter = Limiter(
    key_func=get_ipaddr,
    storage_uri=f"redis://{settings.databases.redis.args.get("username", "")}:{settings.databases.redis.args.get("password", "")}@{settings.databases.redis.args.get("host", "localhost")}:{settings.databases.redis.args.get("port", 6379)}",
    default_limits=[settings.rate_limit.by_ip],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    app.state.limiter = limiter

    models.registry = ModelRegistry(settings=settings.models)
    if settings.internet:
        internet.search = InternetClient.import_module(type=settings.internet.type)(**settings.internet.args)
    else:
        internet.search = None

    # databases
    if settings.databases.qdrant:
        type = settings.databases.qdrant.type
        args = settings.databases.qdrant.args
    elif settings.databases.elastic:
        type = settings.databases.elastic.type
        args = settings.databases.elastic.args
    else:
        type = None
        args = None

    databases.search = SearchClient.import_module(type=type)(models=models.registry, **args) if type and args else None
    databases.cache = CacheClient(connection_pool=ConnectionPool(**settings.databases.redis.args))
    databases.auth = AuthenticationClient(cache=databases.cache, **settings.databases.grist.args) if settings.databases.grist else None

    # Store databases in app.state for middleware access
    app.state.databases = databases

    yield

    if databases.search:
        databases.search.close()
