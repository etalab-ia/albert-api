from abc import ABC, abstractmethod
from asyncio import Lock
from itertools import cycle
import time

from app.clients.model import BaseModelClient as ModelClient
from app.schemas.models import ModelCosts, ModelType


class BaseModelRouter(ABC):
    def __init__(
        self,
        id: str,
        type: ModelType,
        owned_by: str,
        aliases: list[str],
        routing_strategy: str,
        clients: list[ModelClient],
        *args,
        **kwargs,
    ) -> None:
        vector_sizes, max_context_lengths, costs = list(), list(), list()

        for client in clients:
            vector_sizes.append(client.vector_size)
            max_context_lengths.append(client.max_context_length)
            costs.append(client.costs)

        # consistency checks
        assert len(set(vector_sizes)) < 2, "All embeddings models in the same model group must have the same vector size."

        # if there are several models with different max_context_length, it will return the minimal value for consistency of /v1/models response
        max_context_lengths = [value for value in max_context_lengths if value is not None]
        max_context_length = min(max_context_lengths) if max_context_lengths else None

        # if there are several models with different costs, it will return the max value for consistency of /v1/models response
        prompt_tokens = max(costs.prompt_tokens for costs in costs)
        completion_tokens = max(costs.completion_tokens for costs in costs)
        costs = ModelCosts(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

        # set attributes of the model (returned by /v1/models endpoint)
        self.id = id
        self.type = type
        self.owned_by = owned_by
        self.created = round(time.time())
        self.aliases = aliases
        self.max_context_length = max_context_length
        self.costs = costs

        self._vector_size = vector_sizes[0]
        self._routing_strategy = routing_strategy
        self._cycle = cycle(clients)
        self._clients = clients

        self._lock = Lock()

    @abstractmethod
    async def get_client(self, endpoint: str) -> ModelClient:
        """
        Get a client to handle the request

        Args:
            endpoint(str): The type of endpoint called

        Returns:
            BaseModelClient: The available client
        """
        pass

    async def add_client(self, client: ModelClient):
        """
        Adds a new client.
        """
        pass

    async def delete_client(self, api_url: str, model: str):
        """
        Delete a client.
        """
        pass
