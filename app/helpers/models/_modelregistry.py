from asyncio import Lock, wait_for
from typing import List, Optional, Callable, Union, Awaitable, TYPE_CHECKING

import aio_pika

from app.helpers.models._workingcontext import WorkingContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.core.configuration import RoutingStrategy
from app.schemas.models import Model as ModelSchema, ModelType
from app.utils.configuration import configuration
from app.utils.exceptions import ModelNotFoundException

from app.helpers.models.routers import ModelRouter
from app.utils.rabbitmq import AsyncRabbitMQConnection

if TYPE_CHECKING:
    # only for type‐checkers and linters, not at runtime
    # Used to break circular import
    from app.clients.model import BaseModelClient
from app.utils.variables import DEFAULT_APP_NAME

from app.helpers._modeldatabasemanager import ModelDatabaseManager


class ModelRegistry:
    def __init__(self, routers: List[ModelRouter]) -> None:
        self._router_ids = list()
        self._routers = dict()
        self.aliases = dict()
        self._lock = Lock()

        for r in routers:
            if "name" not in r.__dict__:  # no clients available
                continue

            self._routers[r.name] = r
            self._router_ids.append(r.name)

            for alias in r.aliases:
                self.aliases[alias] = r.name

    async def __call__(self, model: str) -> ModelRouter:
        async with self._lock:
            model = self.aliases.get(model, model)

            if model in self._router_ids:
                return self._routers[model]

        raise ModelNotFoundException()

    async def get_original_name(self, model: str) -> str:
        """
        Given an alias, returns the original name of the model.
        Given an original name, simply returns it.

        Args:
            model(str): A model name.

        Returns:
            The original name of the model.
        """
        async with self._lock:
           return self.aliases.get(model, model)

    async def list(self, model: Optional[str] = None) -> List[ModelSchema]:
        data = list()
        async with self._lock:
            models = [model] if model else self._router_ids
            for model in models:
                # Avoid self.__call__, deadlock otherwise
                model = self._routers[self.aliases.get(model, model)]

                data.append(
                    ModelSchema(
                        id=model.name,
                        type=model.type,
                        max_context_length=model.max_context_length,
                        owned_by=model.owned_by,
                        created=model.created,
                        aliases=model.aliases,
                        costs={"prompt_tokens": model.cost_prompt_tokens, "completion_tokens": model.cost_completion_tokens},
                    )
                )

        return data

    async def __add_client_to_existing_router(
        self,
        router_name: str,
        model_client: "BaseModelClient",
        session: AsyncSession,
        **__
    ):
        """
        Adds a new client to an existing ModelRouter. Method is thread-unsafe.

        Args:
            model_client(ModelClient): The model client itself.
            router_name(str): The id of the ModelRouter.
            session(AsyncSession): Database session.
        """
        assert router_name in self._routers, f"No ModelRouter has ID {router_name}."

        await ModelDatabaseManager.add_client(session, router_name, model_client.as_schema(censored=False))
        await self._routers[router_name].add_client(model_client)

    async def __add_client_to_new_router(
        self,
        router_name: str,
        model_client: "BaseModelClient",
        session: AsyncSession,
        model_type: ModelType = None,
        aliases: List[str] = None,
        routing_strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN,
        owner: str = None,
        **__
    ):
        """
        Adds a new client to a new ModelRouter. Method is thread-unsafe.

        Args:
            model_client(ModelClient): The model client itself.
            model_type(ModelType): The type of model.
            session(AsyncSession): Database session.
            router_name(str): The id of the ModelRouter.
            aliases(List[str]): The list of aliases of the ModelRouter.
            routing_strategy: The routing strategy (ie how a ModelRouter choose a ModelClient).
            owner: The owner of the ModelRouter.
        """

        assert model_type is not None, "A ModelType needs to be provided"
        assert router_name not in self._routers, "A ModelRouter with id {router_id} already exists"
        assert owner, "An owner needs to be provided to create a ModelRouter"

        if aliases is None:
            aliases = []

        router = ModelRouter(
            name=router_name,
            type=model_type,
            owned_by=owner,
            aliases=aliases,
            routing_strategy=routing_strategy,
            providers=[model_client],
        )
        await ModelDatabaseManager.add_router(session, await router.as_schema(censored=False))

        self._routers[router_name] = router

        for a in aliases:
            if a not in self.aliases:
                self.aliases[a] = router_name

    async def add_client(
        self,
        router_name: str,
        model_client: "BaseModelClient",
        session: AsyncSession,
        **kwargs
    ):
        """
        Adds a new client, and creates a ModelRouter if needed.
        This method is thread safe.

        Args:
            model_client(ModelClient): The model client itself.
            router_name(str): ID of the targeted ModelRouter. IT can be an alias.
            session(AsyncSession): Database session.
            kwargs: Additional arguments, mainly for ModelRouter creation.
                Must contain at least a model_type to create a ModelRouter.
        """

        async with self._lock:

            router_name = self.aliases.get(router_name, router_name)  # If alias, gets id.

            if router_name in self._routers: # ModelRouter exists
                # For now, there is no "owned_by" field in ModelClient, so config's ModelClient
                # are not distinguishable from provider's. Thus, no ModelClient can be removed from config's
                # ModelRouter for safety, so we have to prevent their addition too.
                assert self._routers[router_name].owned_by != DEFAULT_APP_NAME, "Owner cannot be the API itself"
                await self.__add_client_to_existing_router(
                    router_name, model_client, session, **kwargs
                )
            else:
                await self.__add_client_to_new_router(
                    router_name, model_client, session, **kwargs
                )

            self._router_ids.append(router_name)

    async def delete_client(self, router_name: str, api_url: str, model_name: str, session: AsyncSession):
        """
        Removes a client.

        Args:
            router_name(str): id of the ModelRouter instance, where lies the ModelClient.
            api_url(str): The model API URL.
            model_name(str): The model name.
            session(AsyncSession): Database session.
        """
        async with self._lock:
            assert router_name in self._routers, f"No ModelRouter has ID {router_name}"

            router = self._routers[router_name]

            assert router.owned_by != DEFAULT_APP_NAME, "Owner cannot be the API itself"

            # ModelClient is removed within instance lock to prevent
            # any other threads to access self._routers or self.router_ids before we completely removed
            # the client.
            await ModelDatabaseManager.delete_client(session, router_name, model_name, api_url)
            still_has_clients = await router.delete_client(api_url, model_name)

            if not still_has_clients:
                # ModelRouter with no clients left gets wipe out.
                await ModelDatabaseManager.delete_router(session, router_name)
                aliases = [al for al, model_id in self.aliases.items() if model_id == router_name]
                for a in aliases:
                    del self.aliases[a]

                del self._routers[router_name]
                self._router_ids.remove(router_name)

    async def add_aliases(self, router_name: str, aliases: List[str], session: AsyncSession):
        """
        Adds aliases of a ModelRouter.

        Args:
            router_name(str): The ID of a ModelRouter. Can also be an alias itself.
            aliases(List(str)): aliases to add.
            session(AsyncSession): Database session.
        """
        async with self._lock:
            assert router_name in self.aliases or router_name in self._router_ids, f"ModelRouter \"{router_name}\" does not exist."
            router_name = self.aliases.get(router_name, router_name)

            assert self._routers[router_name].owned_by != DEFAULT_APP_NAME, "Cannot edit API routers aliases."

            for al in aliases:
                if al not in self.aliases:  # Error when alias linked to another ModelRouter?
                    await ModelDatabaseManager.add_alias(session, router_name, al)
                    self.aliases[al] = router_name
                    await self._routers[router_name].add_alias(al)

    async def delete_aliases(self, router_name: str, aliases: List[str], session: AsyncSession):
        """
        Removes aliases of a ModelRouter.

        Args:
            router_name(str): The ID of a ModelRouter. Can also be an alias itself.
            aliases(List(str)): aliases to remove.
            session(AsyncSession): Database session.
        """
        async with self._lock:
            assert router_name in self.aliases or router_name in self._router_ids, f"ModelRouter \"{router_name}\" does not exist."
            router_name = self.aliases.get(router_name, router_name)

            assert self._routers[router_name].owned_by != DEFAULT_APP_NAME, "Cannot edit API routers aliases."

            for al in aliases:
                if al in self.aliases and self.aliases[al]:  # Error when alias linked to another ModelRouter?
                    await ModelDatabaseManager.delete_alias(session, router_name, al)
                    del self.aliases[al]
                    await self._routers[router_name].delete_alias(al)

    async def get_models(self) -> List[str]:
        """
        Get all ModelRouter IDs.
        """
        async with self._lock:
            return self._router_ids

    async def get_router_instances(self) -> List[ModelRouter]:
        """
        Returns existing ModelRouter instances.
        """
        async with self._lock:
            return [r for r in self._routers.values()]

    async def execute_request[R](
        self,
        router_id: str,
        endpoint: str,
        handler: Callable[["BaseModelClient"], Union[R, Awaitable[R]]]
    ) -> R:
        """
        Execute an endpoint's request at the right location.
            If RabbitMQ is enabled, it passes the request to the right queue, and wait for the result.
            If not, it directly gets a ModelClient to send the request.

        In both case, this method is thread-safe, and should be the main way to send a request to a
          remote LLM and retrieve the result.

        Args:
              router_id(str): the ModelRouter name the end user wants to access.
              endpoint(str): the AI API endpoint to send the request to.
              handler(callable): A callback that, given a ModelClient, returns the wished result.
                It describes the actual "work" to be done.

        Returns: Whatever the handler returns.
        """

        # We lock to prevent any race condition while working
        async with self._lock:

            router_id = self.aliases.get(router_id, router_id)

            if router_id not in self._router_ids:
                raise ModelNotFoundException()

            model_router = self._routers[router_id]

            if configuration.dependencies.rabbitmq:  # RabbitMQ is on
                ctx = WorkingContext(
                    endpoint=endpoint,
                    handler=handler
                )

                await model_router.register_context(ctx)

                try:
                    await AsyncRabbitMQConnection().publish_default_exchange(
                        message=aio_pika.Message(body=ctx.id.encode('utf8')),
                        routing_key=model_router.queue_name
                    )

                    result = await wait_for(ctx.result, timeout=configuration.dependencies.rabbitmq.timeout)
                    await model_router.pop_context(ctx)  # free space once finished
                    return result

                except Exception as e:
                    # Anyway, we pop the context, to prevent memory leaks
                    await model_router.pop_context(ctx.id)
                    raise e

            # if no RabbitMQ, classic access
            return await model_router.safe_client_access(
                endpoint=endpoint,
                handler=handler
            )
