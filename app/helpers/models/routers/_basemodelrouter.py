from abc import ABC, abstractmethod
from asyncio import Lock
from itertools import cycle
import time
from typing import Callable, Union, Awaitable
import inspect

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
        self.routing_strategy = routing_strategy
        self._cycle = cycle(clients)
        self._clients = clients

        self._lock = Lock()

    @abstractmethod
    def get_client(self, endpoint: str) -> ModelClient:
        """
        Get a client to handle the request.
        NB: this method is not thread-safe, you probably want to use safe_client_access.

        Args:
            endpoint(str): The type of endpoint called

        Returns:
            BaseModelClient: The available client
        """
        pass

    async def get_clients(self):
        """
        Return the current list of ModelClient thread-safely.
        """
        async with self._lock:
            return self._clients

    async def add_client(self, client: ModelClient):
        """
        Adds a new client.
        """
        async with self._lock:
            for c in self._clients:
                if c.api_url == client.api_url: # The client already exists; we don't want to double it
                    return

            self._clients.append(client)

            # consistency checks

            if client.vector_size != self._vector_size:
                raise ValueError("All embeddings models in the same model group must have the same vector size.")

            if client.max_context_length is not None:
                if self.max_context_length is None:
                    self.max_context_length = client.max_context_length
                else:
                    self.max_context_length = min(self.max_context_length, client.max_context_length)

            self._cycle = cycle(self._clients)
            prompt_tokens = max(self.costs.prompt_tokens, client.costs.prompt_tokens)
            completion_tokens = max(self.costs.completion_tokens, client.costs.completion_tokens)
            self.costs = ModelCosts(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
            # TODO: add to DB (with lock, in case delete is called right after)

    async def delete_client(self, api_url: str) -> bool:
        """
        Delete a client.

        Returns:
            True if the router still has active ModelClients
            False otherwise
        """
        async with self._lock:
            client = None
            costs = []
            max_context_lengths = []

            for c in self._clients:
                if c.api_url == api_url:
                    client = c
                else:
                    if c.max_context_length is not None:
                        max_context_lengths.append(c.max_context_length)

                    costs.append(c.costs)

            if client is None:
                return len(self._clients) > 0

            await client.lock.acquire()
            self._clients.remove(client)

            self.max_context_length = min(max_context_lengths) if max_context_lengths else None
            self._cycle = cycle(self._clients)

            prompt_tokens = max(costs.prompt_tokens for costs in costs)
            completion_tokens = max(costs.completion_tokens for costs in costs)
            self.costs = ModelCosts(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

            client.lock.release()
            # TODO: remove from DB
            return len(self._clients) > 0

    async def safe_client_access[R](
            self,
            endpoint: str,
            handler: Callable[[ModelClient], Union[R, Awaitable[R]]]
    ) -> R:
        """
        Thread-safely access a BaseModelClient.
        This method calls the given callback with the current instance and BaseModelClient
            lock acquired just in time, to prevent race conditions on the selected BaseModelClient.
        Unattended disconnections may still happen (the function may raise an HTTPException).
        """
        async with self._lock:
            client = self.get_client(endpoint)
            # Client lock is acquired within this block to prevent
            # another thread to remove it while in use
            await client.lock.acquire()

        if inspect.iscoroutinefunction(handler):
            result = await handler(client)
        else:
            result = handler(client)

        client.lock.release()
        return result
