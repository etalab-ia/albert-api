from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI

from app.clients.database import SQLDatabaseClient
from app.clients.internet import BaseInternetClient as InternetClient
from app.clients.search import BaseSearchClient as SearchClient
from app.clients.model import BaseModelClient as ModelClient
from app.helpers import AuthManager, ModelRegistry
from app.utils.settings import settings
from app.helpers import ModelRouter
from app.utils.logging import logger
import traceback

auth = SimpleNamespace()
internet = SimpleNamespace()
models = SimpleNamespace()
databases = SimpleNamespace()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    auth.manager = AuthManager(client=SQLDatabaseClient(**settings.databases.sql.args))

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
            continue
        logger.info(msg=f"add model {model.id} ({len(clients)}/{len(model.clients)} clients).")
        model = model.model_dump()
        model["clients"] = clients
        routers.append(ModelRouter(**model))
    models.registry = ModelRegistry(routers=routers)

    internet.search = InternetClient.import_module(type=settings.internet.type)(**settings.internet.args)

    # @TODO: split search between Client and Manager
    type = settings.databases.qdrant.type if settings.databases.qdrant else settings.databases.elastic.type
    args = settings.databases.qdrant.args if settings.databases.qdrant else settings.databases.elastic.args

    databases.search = SearchClient.import_module(type=type)(models=models.registry, auth=auth.manager, **args)

    await auth.manager.setup()

    yield

    # cleanup resources when app shuts down
    databases.search.close()
    await auth.manager.client.engine.dispose()
