from contextlib import asynccontextmanager
import traceback
from types import SimpleNamespace

from coredis import ConnectionPool
from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient

from app.clients.database import SQLDatabaseClient
from app.clients.internet import BaseInternetClient as InternetClient
from app.clients.model import BaseModelClient as ModelClient
from app.helpers import IdentityAccessManager, Limiter, ModelRegistry, ModelRouter, DocumentManager, InternetManager
from app.utils.logging import logger
from app.utils.settings import settings

context = SimpleNamespace()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""
    # setup clients
    sql = SQLDatabaseClient(**settings.databases.sql.args)
    qdrant = AsyncQdrantClient(**settings.databases.qdrant.args)
    redis = ConnectionPool(**settings.databases.redis.args)
    internet = InternetClient.import_module(type=settings.internet.type)(**settings.internet.args)

    # setup context
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
            assert model.id != settings.general["internet_model"], f"Internet model ({model.id}) must be reachable."
            assert model.id != settings.general["documents_model"], f"Documents model ({model.id}) must be reachable."
            continue

        logger.info(msg=f"add model {model.id} ({len(clients)}/{len(model.clients)} clients).")
        model = model.model_dump()
        model["clients"] = clients
        routers.append(ModelRouter(**model))

    context.models = ModelRegistry(routers=routers)
    context.iam = IdentityAccessManager(sql=sql)
    context.limiter = Limiter(connection_pool=redis, strategy=settings.auth.limiting_strategy)
    context.documents = DocumentManager(sql=sql, qdrant=qdrant, internet=InternetManager(internet=internet))

    # await context.iam.setup()
    assert await context.limiter.redis.check(), "Redis database is not reachable."

    yield

    # cleanup resources when app shuts down
    await qdrant.close()
    await sql.engine.dispose()
