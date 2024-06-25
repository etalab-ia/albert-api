from contextlib import asynccontextmanager

from fastapi import FastAPI
from openai import OpenAI

from .config import CONFIG, logging

clients = {"openai": dict(), "chathistory": None, "vectors": None, "files": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    models = list()
    for model in CONFIG["services"]["models"]:
        client = OpenAI(base_url=model["url"], api_key=model.get("key", "EMPTY"), timeout=10)
        try:
            response = client.models.list()
        except Exception as e:
            logging.info(f"error to request the model API on {model['url']}, skipping:\n{e}")  # fmt: off
            continue

        for model in response.data:
            if model.id in models:
                raise ValueError(f"Model id {model.id} is duplicated, not allowed.")
            else:
                models.append(model.id)

            clients["openai"][model.id] = client

    if "openai" not in clients.keys():
        raise ValueError("No model found.")

    # @TODO: support a database set by API key
    for database in CONFIG["services"]["databases"]:
        # chathistory
        if database == "chathistory":
            if CONFIG["services"]["databases"][database]["type"] == "redis":
                from helpers import RedisChatHistory

                clients["chathistory"] = RedisChatHistory(**CONFIG["services"]["databases"][database]["args"])  # fmt: off
            else:
                raise ValueError(f"Chat history database type ({CONFIG[database]['type']}) not supported.")  # fmt: off

        # vectors
        elif database == "vectors":
            if CONFIG["services"]["databases"][database]["type"] == "qdrant":
                from qdrant_client import QdrantClient

                clients["vectors"] = QdrantClient(**CONFIG["services"]["databases"][database]["args"])  # fmt: off
                clients["vectors"].url = CONFIG["services"]["databases"][database]["args"]["url"]
                clients["vectors"].api_key = CONFIG["services"]["databases"][database]["args"]["api_key"]  # fmt: off
            else:
                raise ValueError(f"Vectors database type ({CONFIG[database]['type']}) not supported")  # fmt: off

        # files
        elif database == "files":
            if CONFIG["services"]["databases"][database]["type"] == "minio":
                import boto3
                from botocore.client import Config

                clients["files"] = boto3.client(
                    service_name="s3",
                    config=Config(signature_version="s3v4"),
                    **CONFIG["services"]["databases"][database]["args"],
                )
            else:
                raise ValueError(f"Files database type ({CONFIG['database'][database]['type']}) not supported.")  # fmt: off

        else:
            raise ValueError(f"Database service ({CONFIG['databases'][database]}) not supported.")

    yield  # release ressources when api shutdown
    clients.clear()
