from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI

from app.clients.database import SQLDatabaseClient
from app.clients.internet import BaseInternetClient as InternetClient
from app.clients.search import BaseSearchClient as SearchClient
from app.helpers import AuthManager, ModelRegistry
from app.utils.settings import settings

auth = SimpleNamespace()
internet = SimpleNamespace()
models = SimpleNamespace()
databases = SimpleNamespace()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    auth.manager = AuthManager(client=SQLDatabaseClient(**settings.databases.sql.args))
    internet.search = InternetClient.import_module(type=settings.internet.type)(**settings.internet.args)
    models.registry = ModelRegistry(settings=settings.models)

    # @TODO: split search between Client and Manager
    type = settings.databases.qdrant.type if settings.databases.qdrant else settings.databases.elastic.type
    args = settings.databases.qdrant.args if settings.databases.qdrant else settings.databases.elastic.args

    databases.search = SearchClient.import_module(type=type)(models=models.registry, auth=auth.manager, **args)

    await auth.manager.setup()

    yield

    # cleanup resources when app shuts down
    databases.search.close()
    await auth.manager.client.engine.dispose()
