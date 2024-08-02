from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from openai import OpenAI

from app.utils.config import CONFIG, logging


class ModelDict(dict):
    """
    Overwrite __getitem__ method to raise a 404 error if model is not found.
    """

    def __getitem__(self, key: str):
        try:
            return super().__getitem__(key)
        except KeyError:
            raise HTTPException(status_code=404, detail="Model not found.")


clients = {"models": ModelDict(), "cache": None, "vectors": None, "files": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    models = list()
    for model in CONFIG.models:
        client = OpenAI(base_url=model.url, api_key=model.key, timeout=10)
        try:
            response = client.models.list()
        except Exception as e:
            logging.info(f"error to request the model API on {model.url}, skipping:\n{e}")
            continue

        for model in response.data:
            if model.id in models:
                raise ValueError(f"Model id {model.id} is duplicated, not allowed.")
            else:
                models.append(model.id)

            clients["models"][model.id] = client

    if len(clients["models"].keys()) == 0:
        raise ValueError("No model can be reached.")

    # cache
    if CONFIG.databases.cache.type == "redis":
        from redis import Redis

        clients["cache"] = Redis(**CONFIG.databases.cache.args)

    # vectors
    if CONFIG.databases.vectors.type == "qdrant":
        from qdrant_client import QdrantClient

        clients["vectors"] = QdrantClient(**CONFIG.databases.vectors.args)
        clients["vectors"].url = CONFIG.databases.vectors.args["url"]
        clients["vectors"].api_key = CONFIG.databases.vectors.args["api_key"]

    # files
    if CONFIG.databases.files.type == "minio":
        import boto3
        from botocore.client import Config

        clients["files"] = boto3.client(
            service_name="s3",
            config=Config(signature_version="s3v4"),
            **CONFIG.databases.files.args,
        )

    # auth
    if CONFIG.auth:
        if CONFIG.auth.type == "grist":
            from app.helpers import GristKeyManager

            clients["auth"] = GristKeyManager(redis=clients["cache"], **CONFIG.auth.args)
    else:
        clients["auth"] = None

    yield  # release ressources when api shutdown
    clients.clear()
