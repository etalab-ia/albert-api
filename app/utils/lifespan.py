from contextlib import asynccontextmanager
import traceback
from types import SimpleNamespace

from coredis import ConnectionPool
from fastapi import FastAPI

from app.clients.database import SQLDatabaseClient
from app.clients.internet import BaseInternetClient as InternetClient
from app.clients.model import BaseModelClient as ModelClient
from app.clients.search import BaseSearchClient as SearchClient
from app.helpers import IdentityAccessManager, Limiter, ModelRegistry, ModelRouter
from app.utils.logging import logger
from app.utils.settings import settings

context = SimpleNamespace()
internet = SimpleNamespace()
databases = SimpleNamespace()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

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

    context.models = ModelRegistry(routers=routers)
    context.iam = IdentityAccessManager(sql=SQLDatabaseClient(**settings.databases.sql.args))
    context.limiter = Limiter(connection_pool=ConnectionPool(**settings.databases.redis.args), strategy=settings.auth.limiting_strategy)

    internet.search = InternetClient.import_module(type=settings.internet.type)(**settings.internet.args)

    # @TODO: split search between Client and Manager
    type = settings.databases.qdrant.type if settings.databases.qdrant else settings.databases.elastic.type
    args = settings.databases.qdrant.args if settings.databases.qdrant else settings.databases.elastic.args

    databases.search = SearchClient.import_module(type=type)(models=context.models, auth=context.iam, **args)

    await context.iam.setup()
    assert await context.limiter.redis.check(), "Redis database is not reachable."

    yield

    # cleanup resources when app shuts down
    databases.search.close()
    await context.iam.sql.engine.dispose()
