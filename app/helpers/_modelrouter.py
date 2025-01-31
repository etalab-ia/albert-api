from itertools import cycle
import random
import time
import traceback
from typing import Optional
from urllib.parse import urljoin

import requests

from app.clients.model import BaseModelClient as ModelClient
from app.schemas.settings import Model as ModelSettings
from app.utils.exceptions import WrongModelTypeException
from app.utils.logging import logger
from app.utils.settings import settings as app_settings
from app.utils.variables import (
    MODEL_TYPE__AUDIO,
    MODEL_TYPE__EMBEDDINGS,
    MODEL_TYPE__LANGUAGE,
    MODEL_TYPE__RERANK,
    ROUTER_STRATEGY__ROUND_ROBIN,
    ROUTER_STRATEGY__SHUFFLE,
)


class ModelRouter:
    ENDPOINT_MODEL_TYPE_TABLE = {
        "chat/completions": [MODEL_TYPE__LANGUAGE],
        "embeddings": [MODEL_TYPE__EMBEDDINGS],
        "audio/transcriptions": [MODEL_TYPE__AUDIO],
        "rerank": [MODEL_TYPE__LANGUAGE, MODEL_TYPE__RERANK],
    }

    def __init__(self, model: ModelSettings):
        # check clients of the model
        clients, vector_sizes, max_context_lengths = list(), list(), list()

        for client in model.clients:
            try:
                client = ModelClient.import_module(type=client.type)(settings=client)
                max_context_length = client.models.list().data[0].max_context_length
                max_context_lengths.append(max_context_length)
            except Exception:
                logger.error(msg=f"client of {model.id} is unavailable: skipping.")
                logger.debug(msg=traceback.format_exc())
                continue

            vector_size = None
            if model.type == MODEL_TYPE__EMBEDDINGS:
                response = requests.post(
                    url=urljoin(base=str(client.base_url), url=client.ENDPOINT_TABLE["embeddings"]),
                    headers={"Authorization": f"Bearer {client.api_key}"},
                    json={"model": client.model, "input": "hello world"},
                    timeout=client.timeout,
                )
                assert response.status_code == 200, f"Failed to get vector size for {client.model}: {response.text} ({response.status_code})."

                vector_size = len(response.json()["data"][0]["embedding"])

            vector_sizes.append(vector_size)
            clients.append(client)

        if not clients:
            logger.error(msg=f"adding {model.id} - no clients: skipping.")
            return None

        # consistency checks
        assert len(set(vector_sizes)) < 2, "All embeddings models in the same model group must have the same vector size."

        ## if there are several models with different max_context_length, it will return the minimal value for consistency of /v1/models response
        max_context_lengths = [value for value in max_context_lengths if value is not None]
        max_context_length = min(max_context_lengths) if max_context_lengths else None

        # set attributes of the model (return by /v1/models endpoint)
        self.id = model.id
        self.type = model.type
        self.owned_by = app_settings.app_name
        self.created = round(time.time())
        self.aliases = model.aliases
        self.max_context_length = max_context_length

        self._vector_size = vector_sizes[0]
        self._default_internet = model.default_internet
        self._routing_strategy = model.routing_strategy
        self._cycle = cycle(clients)
        self._clients = clients

        logger.info(msg=f"adding {model.id}: done.")

    def get_client(self, endpoint: Optional[str] = None) -> ModelClient:
        if endpoint and self.type not in self.ENDPOINT_MODEL_TYPE_TABLE[endpoint]:
            raise WrongModelTypeException()

        if self._routing_strategy == ROUTER_STRATEGY__ROUND_ROBIN:
            return next(self._cycle)
        elif self._routing_strategy == ROUTER_STRATEGY__SHUFFLE:
            return random.choice(self._clients)

    def _routing_strategy_shuffle(self) -> ModelClient:
        return random.choice(self._clients)

    def _routing_strategy_round_robin(self) -> ModelClient:
        return next(self._cycle)
