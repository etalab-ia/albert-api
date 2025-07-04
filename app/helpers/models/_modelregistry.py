from asyncio import Lock
from typing import List, Optional

from app.clients.model import BaseModelClient
from app.schemas.models import Model as ModelSchema
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
                model = await self.__call__(model=model)

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

    async def add_client(self, model_client: BaseModelClient, provider: str):
        """
        Adds a new client.

        Args:
            model_client(ModelClient): The model client itself.
            provider(str): Provider API key (used as a unique ID).
        """
        pass

    async def remove_client(self, api_url: str, model_type: str, provider: str):
        """
        Removes a client.

        Args:
            api_url(str): The model API URL.
            model_type(str): The model kind. With the API, uniquely identify the model entry.
            provider(str): Provider API key (used as a unique ID).
        """
        pass

    async def get_models(self) -> List[ModelRouter]:
        """
        Get all ModelRouter.
        """
        async with self._lock:
            return self.models
