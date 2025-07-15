import asyncio
import functools
import threading
from abc import ABC, abstractmethod
from asyncio import Lock
from itertools import cycle
import time
from typing import Callable, Union, Awaitable
import inspect
from uuid import uuid4

from app.clients.model import BaseModelClient as ModelClient
from app.helpers.models._workingcontext import WorkingContext
from app.schemas.models import ModelType
from app.utils.configuration import configuration
from app.utils.rabbitmq import ConsumerRabbitMQConnection


def sync(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # TODO create new event loop each time sucks
        return asyncio.new_event_loop().run_until_complete(f(*args, **kwargs))
    return wrapper


class BaseModelRouter(ABC):
    def __init__(
        self,
        name: str,
        type: ModelType,
        owned_by: str,
        aliases: list[str],
        routing_strategy: str,
        providers: list[ModelClient],
        *args,
        **kwargs,
    ) -> None:
        vector_sizes, max_context_lengths, costs_prompt_tokens, costs_completion_tokens = list(), list(), list(), list()

        for provider in providers:
            vector_sizes.append(provider.vector_size)
            max_context_lengths.append(provider.max_context_length)
            costs_prompt_tokens.append(provider.cost_prompt_tokens)
            costs_completion_tokens.append(provider.cost_completion_tokens)

        # consistency checks
        assert len(set(vector_sizes)) < 2, "All embeddings models in the same model group must have the same vector size."

        # if there are several models with different max_context_length, it will return the minimal value for consistency of /v1/models response
        max_context_lengths = [value for value in max_context_lengths if value is not None]
        max_context_length = min(max_context_lengths) if max_context_lengths else None

        # if there are several models with different costs, it will return the max value for consistency of /v1/models response
        prompt_tokens = max(costs_prompt_tokens)
        completion_tokens = max(costs_completion_tokens)

        # set attributes of the model (returned by /v1/models endpoint)
        self.name = name
        self.type = type
        self.owned_by = owned_by
        self.created = round(time.time())
        self.aliases = aliases
        self.max_context_length = max_context_length
        self.cost_prompt_tokens = prompt_tokens
        self.cost_completion_tokens = completion_tokens

        self.vector_size = vector_sizes[0]
        self.routing_strategy = routing_strategy
        self._cycle = cycle(providers)
        self._providers = providers

        self._lock = Lock()

        self._context_lock = Lock()
        self._context_register = dict()

        self.queue_name = str(uuid4())  # TODO maybe use type + name?

        if configuration.dependencies.rabbitmq:
            channel = ConsumerRabbitMQConnection().channel
            channel.queue_declare(queue=self.queue_name)
            channel.basic_consume(queue=self.queue_name, auto_ack=True, on_message_callback=lambda *cargs: self._queue_callback(*cargs))
            threading.Thread(target=channel.start_consuming).start()

    @sync
    async def _queue_callback(self, channel, method, properties, body):
        print("[*] Callback!")
        ctx = await self.get_context(body.decode('utf8'))
        if ctx is None:
            return

        async with self._lock:
            client = self.get_client(ctx.endpoint)
            await client.lock.acquire()

        ctx.complete(client)
        client.lock.release()


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
            return self._providers

    async def add_client(self, client: ModelClient):
        """
        Adds a new client.
        """
        async with self._lock:
            for c in self._providers:
                if c.url == client.url and c.name == client.name: # The client already exists; we don't want to double it
                    return

            self._providers.append(client)

            # consistency checks

            if client.vector_size != self.vector_size:
                raise ValueError("All embeddings models in the same model group must have the same vector size.")

            if client.max_context_length is not None:
                if self.max_context_length is None:
                    self.max_context_length = client.max_context_length
                else:
                    self.max_context_length = min(self.max_context_length, client.max_context_length)

            self._cycle = cycle(self._providers)
            self.cost_prompt_tokens = max(self.cost_prompt_tokens, client.cost_prompt_tokens)
            self.cost_completion_tokens = max(self.cost_completion_tokens, client.cost_completion_tokens)
            # TODO: add to DB (with lock, in case delete is called right after)

    async def delete_client(self, api_url: str, name: str) -> bool:
        """
        Delete a client.

        Returns:
            True if the router still has active ModelClients
            False otherwise
        """
        async with self._lock:
            client = None
            cost_prompt_tokens = self.cost_prompt_tokens
            cost_completion_tokens = self.cost_completion_tokens
            max_context_length = self.max_context_length
            costs = []
            max_context_lengths = []

            for c in self._providers:
                if c.url == api_url and c.name == name:
                    client = c
                else:
                    if c.max_context_length is not None and c.max_context_length > max_context_length:
                        max_context_length = c.max_context_length

                    if c.cost_prompt_tokens > cost_prompt_tokens:
                        cost_prompt_tokens = c.cost_prompt_tokens

                    if c.cost_completion_tokens > c.cost_completion_tokens:
                        cost_completion_tokens = c.cost_completion_tokens

            if client is None:
                return len(self._providers) > 0

            await client.lock.acquire()
            self._providers.remove(client)

            if len(self._providers) == 0:
                # No more clients, the ModelRouter is about to get deleted.
                # There is no need to try to "update" it further.
                # NB: there is no chance that another ModelClient gets added right after,
                # as ModelRegistry's requires its lock for the whole removing process.
                # If needed, "this" router will be recreated.
                client.lock.release()  # Who knows
                return False

            self.max_context_length = min(max_context_lengths) if max_context_lengths else None
            self._cycle = cycle(self._providers)

            self.cost_prompt_tokens = cost_prompt_tokens
            self.cost_completion_tokens = cost_completion_tokens
            self.max_context_length = max_context_length

            client.lock.release()
            # TODO: remove from DB
            return True

    async def add_alias(self, alias: str):
        """
        Thread-safely adds an alias.
        """
        async with self._lock:
            if alias not in self.aliases:  # Silent error?
                self.aliases.append(alias)

    async def delete_alias(self, alias):
        """
        Thread-safely removes an alias.
        """
        async with self._lock:
            if alias in self.aliases:  # Silent error?
                self.aliases.remove(alias)

    async def register_context(self, req_ctx: WorkingContext):
        async with self._context_lock:  # We use a different lock as this operation has nothing to do with other fields
            self._context_register[req_ctx.id] = req_ctx

    async def pop_context(self, ctx_id: str) -> WorkingContext | None:
        async with self._context_lock:

            if ctx_id not in self._context_register:
                return None

            return self._context_register.pop(ctx_id)

    async def get_context(self, ctx_id: str) -> WorkingContext | None:
        async with self._context_lock:
            return self._context_register.get(ctx_id, None)

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
