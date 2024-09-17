import time
from contextlib import asynccontextmanager
from functools import partial
from typing import Dict, List

import requests
from fastapi import FastAPI, HTTPException
from openai import OpenAI

from app.schemas.config import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE, METADATA_COLLECTION
from app.schemas.models import Model, Models
from app.utils.config import CONFIG, LOGGER


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


# @TODO: create a ClientsManager helper to manage clients
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to initialize clients (models API and databases)."""

    # @TODO: add cache
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
            assert len(response["data"]) == 1, "Only one model per model API is supported."
            response = response["data"][0]
            data.append(
                Model(
                    id=response["id"],
                    object="model",
                    owned_by=response.get("owned_by", ""),
                    created=response.get("created", round(time.time())),
                    max_model_len=response.get("max_model_len", None),
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
        else:
            raise HTTPException(status_code=400, detail="Model type not supported.")

        return Models(data=data)

    def check_context_length(self, model: str, messages: List[Dict[str, str]], add_special_tokens: bool = True):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        prompt = "\n".join([message["role"] + ": " + message["content"] for message in messages])
        data = {"model": model, "prompt": prompt, "add_special_tokens": add_special_tokens}

        response = requests.post(str(self.base_url).replace("/v1/", "/tokenize"), json=data, headers=headers)
        response.raise_for_status()
        return response.json()["count"] <= response.json()["max_model_len"]

    models = list()
    for model in CONFIG.models:
        client = OpenAI(base_url=model.url, api_key=model.key, timeout=10)
        client.type = model.type
        client.models.list = partial(get_models_list, client)

        try:
            response = client.models.list()
            model = response.data[0]
            if model.id in models:
                raise ValueError(f"Model id {model.id} is duplicated, not allowed.")
        except Exception as e:
            LOGGER.info(f"error to request the model API on {model.url}, skipping:\n{e}")
            continue

        models.append(model.id)
        # get vector size
        if client.type == EMBEDDINGS_MODEL_TYPE:
            response = client.embeddings.create(model=model.id, input="hello world")
            client.vector_size = len(response.data[0].embedding)

        if client.type == LANGUAGE_MODEL_TYPE:
            client.check_context_length = partial(check_context_length, client)

        clients["models"][model.id] = client

    if len(clients["models"].keys()) == 0:
        raise ValueError("No model can be reached.")

    # cache

    from redis import Redis

    clients["cache"] = Redis(**CONFIG.databases.cache.args)

    # vectors
    from qdrant_client import QdrantClient

    clients["vectors"] = QdrantClient(**CONFIG.databases.vectors.args)
    clients["vectors"].url = CONFIG.databases.vectors.args["url"]
    clients["vectors"].api_key = CONFIG.databases.vectors.args["api_key"]

    if not clients["vectors"].collection_exists(collection_name=METADATA_COLLECTION):
        clients["vectors"].create_collection(collection_name=METADATA_COLLECTION, vectors_config={}, on_disk_payload=False)

    # files
    import boto3
    from botocore.client import Config

    clients["files"] = boto3.client(
        service_name="s3",
        config=Config(signature_version="s3v4"),
        **CONFIG.databases.files.args,
    )

    # auth
    if CONFIG.auth:
        from app.helpers import GristKeyManager

        clients["auth"] = GristKeyManager(redis=clients["cache"], **CONFIG.auth.args)
    else:
        clients["auth"] = None

    yield  # release ressources when api shutdown
    clients.clear()
