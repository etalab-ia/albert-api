from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import Limiter
from slowapi.util import get_ipaddr

from app.helpers import ClientsManager
from app.utils.settings import settings

clients = ClientsManager(settings=settings)
limiter = Limiter(
    key_func=get_ipaddr,
    storage_uri=f"redis://{settings.clients.cache.args.get("username", "")}:{settings.clients.cache.args.get("password", "")}@{settings.clients.cache.args["host"]}:{settings.clients.cache.args["port"]}",
    default_limits=[settings.rate_limit.by_ip],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    app.state.limiter = limiter
    clients.set()

    yield

    clients.clear()
