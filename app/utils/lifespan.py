from contextlib import asynccontextmanager
import requests
import time
from functools import partial

from fastapi import FastAPI, HTTPException
from openai import OpenAI

from app.utils.config import CONFIG, LOGGER
from app.schemas.config import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE, METADATA_COLLECTION, AUDIO_MODEL_TYPE
from app.schemas.models import Model, Models


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

    def get_models_list(self, *args, **kwargs):
        """
        Custom method to overwrite OpenAI's list method (client.models.list()). This method support
        embeddings API models deployed with HuggingFace Text Embeddings Inference (see: https://github.com/huggingface/text-embeddings-inference).
        """
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        data = list()

        if self.type == LANGUAGE_MODEL_TYPE:
            endpoint = f"{self.base_url}models"
            response = requests.get(url=endpoint, headers=headers, timeout=10).json()
            for row in response["data"]:
                data.append(
                    Model(
                        id=row["id"],
                        object="model",
                        owned_by=row.get("owned_by", ""),
                        created=row.get("created", round(time.time())),
                        max_model_len=row.get("max_model_len", None),
                        type=LANGUAGE_MODEL_TYPE,
                    )
                )

        elif self.type == EMBEDDINGS_MODEL_TYPE:
            endpoint = str(self.base_url).replace("/v1/", "/info")
            response = requests.get(url=endpoint, headers=headers, timeout=10).json()
            data.append(
                Model(
                    id=response["model_id"],
                    object="model",
                    owned_by="huggingface-text-embeddings-inference",
                    max_model_len=response.get("max_input_length", None),
                    created=round(time.time()),
                    type=EMBEDDINGS_MODEL_TYPE,
                )
            )
        elif self.type == AUDIO_MODEL_TYPE:
            data.append(
                Model(
                    id="Systran/faster-distil-whisper-large-v3", #todo: fix this & find a way to get the model id from the api?
                    object="model",
                    owned_by="openai",
                    max_model_len=None,
                    created=round(time.time()),
                    type=AUDIO_MODEL_TYPE,
                )
            )
        else:
            raise HTTPException(status_code=400, detail="Model type not supported.")

        return Models(data=data)

    models = list()
    for model in CONFIG.models:
        client = OpenAI(base_url=model.url, api_key=model.key, timeout=10)
        client.type = model.type
        client.models.list = partial(get_models_list, client)

        try:
            response = client.models.list()
        except Exception as e:
            LOGGER.info(f"error to request the model API on {model.url}, skipping:\n{e}")
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

        if not clients["vectors"].collection_exists(collection_name=METADATA_COLLECTION):
            clients["vectors"].create_collection(
                collection_name=METADATA_COLLECTION, vectors_config={}, on_disk_payload=False
            )

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
