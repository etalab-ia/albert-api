from asyncio import Lock
from typing import List, Optional

from app.clients.model import BaseModelClient
from app.schemas.core.models import RoutingStrategy
from app.schemas.models import Model as ModelSchema, ModelType
from app.utils.exceptions import ModelNotFoundException

from app.helpers.models.routers import ModelRouter


class ModelRegistry:
    def __init__(self, routers: List[ModelRouter]) -> None:
        self.models = list()
        self.aliases = dict()
        self._lock = Lock()

        for model in routers:
            if "id" not in model.__dict__:  # no clients available
                continue

            self.__dict__[model.id] = model
            self.models.append(model.id)

            for alias in model.aliases:
                self.aliases[alias] = model.id

    async def __call__(self, model: str) -> ModelRouter:
        async with self._lock:
            model = self.aliases.get(model, model)

            if model in self.models:
                return self.__dict__[model]

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
            models = [model] if model else self.models
            for model in models:
                # Avoid self.__call__, deadlock otherwise
                model = self.__dict__[self.aliases.get(model, model)]

                data.append(
                    ModelSchema(
                        id=model.id,
                        type=model.type,
                        max_context_length=model.max_context_length,
                        owned_by=model.owned_by,
                        created=model.created,
                        aliases=model.aliases,
                        costs=model.costs,
                    )
                )

        return data

    async def __add_client_to_existing_router(
        self,
        router_id: str,
        model_client: BaseModelClient,
        **__
    ):
        """
        Adds a new client to an existing ModelRouter. Method is thread-unsafe.

        Args:
            model_client(ModelClient): The model client itself.
            router_id(str): The id of the ModelRouter.
        """
        assert router_id in self.__dict__, f"No ModelRouter has ID {router_id}."

        await self.__dict__[router_id].add_client(model_client)
        # TODO: add ModelClient to DB.


    async def __add_client_to_new_router(
        self,
        router_id: str,
        model_client: BaseModelClient,
        model_type: ModelType = None,
        aliases: List[str] = None,
        routing_strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN,
        owner: str = "Albert API",
        **__
    ):
        """
        Adds a new client to a new ModelRouter. Method is thread-unsafe.

        Args:
            model_client(ModelClient): The model client itself.
            model_type(ModelType): The type of model.
            router_id(str): The id of the ModelRouter.
            aliases(List[str]): The list of aliases of the ModelRouter.
            routing_strategy: The routing strategy (ie how a ModelRouter choose a ModelClient).
            owner: The owner of the ModelRouter.
        """

        assert model_type is not None, "A ModelType needs to be provided"
        assert router_id not in self.__dict__, "A ModelRouter with id {router_id} already exists"

        if aliases is None:
            aliases = []

        router = ModelRouter(
            id=router_id,
            type=model_type,
            owned_by=owner,
            aliases=aliases,
            routing_strategy=routing_strategy,
            clients=[model_client],
        )
        self.__dict__[router_id] = router
        self.models.append(router)

        for a in aliases:
            if a not in self.aliases:
                self.aliases[a] = router_id

        # TODO: add ModelRouter to db
        # TODO: add ModelClient to db

    async def add_client(
        self,
        router_id: str,
        model_client: BaseModelClient,
        **kwargs
    ):
        """
        Adds a new client, and creates a ModelRouter if needed.
        This method is thread safe.

        Args:
            model_client(ModelClient): The model client itself.
            router_id(str): ID of the targeted ModelRouter.
            kwargs: Additional arguments, mainly for ModelRouter creation.
                Must contain at least a model_type to create a ModelRouter.
        """

        async with self._lock:
            if router_id in self.__dict__: # ModelRouter exists
                await self.__add_client_to_existing_router(
                    router_id, model_client, **kwargs
                )
            else:
                await self.__add_client_to_new_router(
                    router_id, model_client, **kwargs
                )

    async def delete_client(self, router_id: str, api_url: str):
        """
        Removes a client.

        Args:
            router_id(str): id of the ModelRouter instance, where lies the ModelClient.
            api_url(str): The model API URL.
        """
        async with self._lock:
            assert router_id in self.__dict__, f"No ModelRouter has ID {router_id}"

            router = self.__dict__[router_id]

            # ModelClient is removed within instance lock to prevent
            # any other threads to access self.__dict__ or self.models before we completely removed
            # the client.
            still_has_clients = await router.delete_client(api_url)

            # TODO ModelClient remove from db.

            if not still_has_clients:
                # ModelRouter with no clients left gets wipe out.
                aliases = [al for al, model_id in self.aliases.items() if model_id == router_id]
                for a in aliases:
                    del self.aliases[a]

                del self.__dict__[router_id]
                self.models.remove(router)
                # TODO remove ModelRouter from db.


    async def get_models(self) -> List[str]:
        """
        Get all ModelRouter IDs.
        """
        async with self._lock:
            return self.models

    async def get_router_instances(self) -> List[ModelRouter]:
        """
        Returns existing ModelRouter instances.
        """
        async with self._lock:
            return [m for m in self.__dict__.values() if isinstance(m, ModelRouter)]
