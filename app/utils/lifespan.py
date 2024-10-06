from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.helpers import ClientsManager
from app.utils.config import CONFIG

clients = ClientsManager(config=CONFIG)


# @TODO: test to move into main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    clients.set()

    yield
