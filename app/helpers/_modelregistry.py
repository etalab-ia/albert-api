from typing import List, Optional

from app.helpers._modelrouter import ModelRouter
from app.schemas.models import Model as ModelSchema
from app.schemas.settings import Model as ModelSettings
from app.utils.exceptions import ModelNotFoundException
from app.utils.variables import (
    MODEL_TYPE__EMBEDDINGS,
    MODEL_TYPE__LANGUAGE,
)


class ModelRegistry:
    def __init__(self, settings: List[ModelSettings]) -> None:
        self.models = list()
        self.aliases = dict()
        self.internet_default_language_model = None
        self.internet_default_embeddings_model = None

        for model in settings:
            model = ModelRouter(model=model)

            if "id" not in model.__dict__:  # no clients available
                continue

            self.__dict__[model.id] = model

            self.models.append(model.id)

            for alias in model.aliases:
                self.aliases[alias] = model.id

            if model._default_internet and model.type == MODEL_TYPE__LANGUAGE:  # set default language internet model
                self.internet_default_language_model = model.id
            if model._default_internet and model.type == MODEL_TYPE__EMBEDDINGS:  # set default embeddings internet model
                self.internet_default_embeddings_model = model.id

        # check if the internet models are available
        if not self.internet_default_language_model:
            raise ValueError("Internet models are not setup.")

    def __getitem__(self, key: str) -> ModelRouter:
        """
        Override the __getitem__ method to return a client model based on the routing strategy.

        Args:
            key (str): The key of the model to get (id or alias). If the model is not found, raise a ModelNotFoundException (404).

        Returns:
            ModelClient: the client model based on the routing strategy.
        """
        key = self.aliases.get(key, key)
        try:
            model = self.__dict__[key]

        except KeyError:
            raise ModelNotFoundException()

        return model

    def list(self, model: Optional[str] = None) -> List[ModelSchema]:
        data = list()
        models = [model] if model else self.models

        for model in models:
            model = self.__getitem__(key=model)
            data.append(
                ModelSchema(
                    id=model.id,
                    type=model.type,
                    max_context_length=model.max_context_length,
                    owned_by=model.owned_by,
                    created=model.created,
                    aliases=model.aliases,
                )
            )

        return data
