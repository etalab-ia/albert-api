from fastapi import HTTPException
from qdrant_client import QdrantClient
from redis import Redis as Cache

from app.schemas.config import Config
from app.utils.config import LOGGER
from app.utils.variables import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE

from ._modelclient import ModelClient
from ._authmanager import AuthManager
from ._vectorstore import VectorStore


class ModelClients(dict):
    """
    Overwrite __getitem__ method to raise a 404 error if model is not found.
    """

    def __init__(self, config: Config):
        for model in config.models:
            try:
                model = ModelClient(base_url=model.url, api_key=model.key, type=model.type, search_internet=model.search_internet)
                self.__setitem__(model.id, model)

            except Exception as e:
                LOGGER.info(f"error to request the model API on {model.url}, skipping:\n{e}")
                continue

            if model.search_internet and model.type == EMBEDDINGS_MODEL_TYPE:
                self.SEARCH_INTERNET_EMBEDDINGS_MODEL_ID = model.id
            if model.search_internet and model.type == LANGUAGE_MODEL_TYPE:
                self.SEARCH_INTERNET_LANGUAGE_MODEL_ID = model.id

        if len(self.keys()) == 0:
            raise ValueError("No model can be reached.")

    def __setitem__(self, key: str, value):
        if any(key == k for k in self.keys()):
            raise KeyError(f"Model id {key} is duplicated, not allowed.")
        super().__setitem__(key, value)

    def __getitem__(self, key: str):
        try:
            return super().__getitem__(key)
        except KeyError:
            raise HTTPException(status_code=404, detail="Model not found.")


class ClientsManager:
    def __init__(self, config: Config):
        self.config = config

    def set(self):
        # set models
        self.models = ModelClients(config=self.config)

        # set cache
        cache = Cache(**self.config.databases.cache.args)
        self.cache = cache

        # set vectors
        vectors = QdrantClient(**self.config.databases.vectors.args)
        self.vectorstore = VectorStore(vectors=vectors, models=self.models)

        # set auth
        auth = AuthManager(redis=self.cache, **self.config.auth.args) if self.config.auth else None
        self.auth = auth
