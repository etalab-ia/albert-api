from typing import List, Optional

from app.schemas.models import Model as ModelSchema
from app.schemas.users import AuthenticatedUser
from app.utils.exceptions import ModelNotFoundException
from app.utils.variables import MODEL_TYPE__EMBEDDINGS, MODEL_TYPE__LANGUAGE

from ._modelrouter import ModelRouter


class ModelRegistry:
    def __init__(self, routers: List[ModelRouter]) -> None:
        self.models = list()
        self.aliases = dict()
        self.internet_default_language_model = None
        self.internet_default_embeddings_model = None

        for model in routers:
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
        if not self.internet_default_language_model or not self.internet_default_embeddings_model:
            raise ValueError("Internet models are not setup.")

    def __call__(self, model: str, user: Optional[AuthenticatedUser] = None) -> ModelRouter:
        model = self.aliases.get(model, model)

        if model in self.models and (not user or user.rpd[model] != 0):
            return self.__dict__[model]
        raise ModelNotFoundException()

    def list(self, model: Optional[str] = None, user: Optional[AuthenticatedUser] = None) -> List[ModelSchema]:
        data = list()
        models = [model] if model else self.models
        for m in models:
            try:
                m = self.get(model=m, user=user)
            except ModelNotFoundException:
                if model:
                    raise ModelNotFoundException()
                continue

            data.append(
                ModelSchema(
                    id=m.id,
                    type=m.type,
                    max_context_length=m.max_context_length,
                    owned_by=m.owned_by,
                    created=m.created,
                    aliases=m.aliases,
                )
            )

        return data
