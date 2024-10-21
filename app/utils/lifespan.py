from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import Limiter
from slowapi.util import get_ipaddr

from app.helpers import ClientsManager
from app.utils.config import CONFIG, GLOBAL_RATE_LIMIT

clients = ClientsManager(config=CONFIG)
limiter = Limiter(
    key_func=get_ipaddr,
    storage_uri=f"redis://{CONFIG.databases.cache.args.get("username", "")}:{CONFIG.databases.cache.args.get("password", "")}@{CONFIG.databases.cache.args["host"]}:{CONFIG.databases.cache.args["port"]}",
    default_limits=[GLOBAL_RATE_LIMIT],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    app.state.limiter = limiter
    clients.set()

    yield

    clients.clear()
