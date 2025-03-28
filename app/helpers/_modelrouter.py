from itertools import cycle
import random
import time

from app.clients.model import BaseModelClient as ModelClient
from app.schemas.core.models import ModelType, RoutingStrategy
from app.schemas.core.settings import Model as ModelSettings
from app.utils.exceptions import WrongModelTypeException
from app.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__RERANK,
)


class ModelRouter:
    ENDPOINT_MODEL_TYPE_TABLE = {
        ENDPOINT__CHAT_COMPLETIONS: [ModelType.LANGUAGE],
        ENDPOINT__EMBEDDINGS: [ModelType.EMBEDDINGS],
        ENDPOINT__AUDIO_TRANSCRIPTIONS: [ModelType.AUDIO],
        ENDPOINT__RERANK: [ModelType.RERANK],
    }

    def __init__(
        self,
        id: str,
        type: ModelType,
        owned_by: str,
        aliases: list[str],
        routing_strategy: str,
        clients: list[ModelSettings],
    ):
        vector_sizes, max_context_lengths = list(), list()

        for client in clients:
            vector_sizes.append(client.vector_size)
            max_context_lengths.append(client.max_context_length)
        # consistency checks
        assert len(set(vector_sizes)) < 2, "All embeddings models in the same model group must have the same vector size."

        # if there are several models with different max_context_length, it will return the minimal value for consistency of /v1/models response
        max_context_lengths = [value for value in max_context_lengths if value is not None]
        max_context_length = min(max_context_lengths) if max_context_lengths else None

        # set attributes of the model (return by /v1/models endpoint)
        self.id = id
        self.type = type
        self.owned_by = owned_by
        self.created = round(time.time())
        self.aliases = aliases
        self.max_context_length = max_context_length

        self._vector_size = vector_sizes[0]
        self._routing_strategy = routing_strategy
        self._cycle = cycle(clients)
        self._clients = clients

    def get_client(self, endpoint: str) -> ModelClient:
        if endpoint and self.type not in self.ENDPOINT_MODEL_TYPE_TABLE[endpoint]:
            raise WrongModelTypeException()

        if self._routing_strategy == RoutingStrategy.ROUND_ROBIN.value:
            client = self._routing_strategy_round_robin()
        else:  # ROUTER_STRATEGY__SHUFFLE
            client = self._routing_strategy_shuffle()

        client.endpoint = endpoint

        return client

    def _routing_strategy_shuffle(self) -> ModelClient:
        return random.choice(self._clients)

    def _routing_strategy_round_robin(self) -> ModelClient:
        return next(self._cycle)
