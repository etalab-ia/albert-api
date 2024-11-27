from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import Limiter
from slowapi.util import get_ipaddr

from app.helpers import ClientsManager
from app.utils.settings import settings

clients = ClientsManager(settings=settings)
limiter = Limiter(
    key_func=get_ipaddr,
    storage_uri=f"redis://{settings.cache.args.get("username", "")}:{settings.cache.args.get("password", "")}@{settings.cache.args["host"]}:{settings.cache.args["port"]}",
    default_limits=[settings.global_rate_limit],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    app.state.limiter = limiter
    clients.set()

    yield

    clients.clear()
