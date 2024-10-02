from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.helpers import ClientsManager
from app.utils.config import CONFIG

clients = ClientsManager(config=CONFIG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    clients.set_models()
    clients.set_cache()
    clients.set_vectors()
    clients.set_auth()

    yield  # release ressources when api shutdown
    clients.clear()
