from abc import ABC, abstractmethod
from itertools import cycle
import time

from app.clients.model import BaseModelClient as ModelClient
from app.schemas.models import ModelType
from app.schemas.core.settings import Model as ModelSettings


class BaseModelRouter(ABC):
    def __init__(
        self,
        id: str,
        type: ModelType,
        owned_by: str,
        aliases: list[str],
        routing_strategy: str,
        clients: list[ModelSettings],
        *args,
        **kwargs,
    ) -> None:
        vector_sizes, max_context_lengths = list(), list()

        for client in clients:
            vector_sizes.append(client.vector_size)
            max_context_lengths.append(client.max_context_length)
        # consistency checks
        assert len(set(vector_sizes)) < 2, "All embeddings models in the same model group must have the same vector size."

        # if there are several models with different max_context_length, it will return the minimal value for consistency of /v1/models response
        max_context_lengths = [value for value in max_context_lengths if value is not None]
        max_context_length = min(max_context_lengths) if max_context_lengths else None

        # set attributes of the model (returned by /v1/models endpoint)
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

    @abstractmethod
    def get_client(self, endpoint: str) -> ModelClient:
        """
        Get a client to handle the request

        Args:
            endpoint(str): The type of endpoint called

        Returns:
            BaseModelClient: The available client
        """
        pass
