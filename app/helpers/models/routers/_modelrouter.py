from app.helpers.models.routers.strategies import RoundRobinRoutingStrategy, ShuffleRoutingStrategy
from app.schemas.core.configuration import RoutingStrategy
from app.schemas.models import ModelType
from app.utils.exceptions import WrongModelTypeException
from app.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS, ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS, ENDPOINT__OCR, ENDPOINT__RERANK

from ._basemodelrouter import BaseModelRouter

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # only for type‐checkers and linters, not at runtime
    # Used to break circular import
    from app.clients.model import BaseModelClient


class ModelRouter(BaseModelRouter):
    ENDPOINT_MODEL_TYPE_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: [ModelType.AUTOMATIC_SPEECH_RECOGNITION],
        ENDPOINT__CHAT_COMPLETIONS: [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__EMBEDDINGS: [ModelType.TEXT_EMBEDDINGS_INFERENCE],
        ENDPOINT__OCR: [ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__RERANK: [ModelType.TEXT_CLASSIFICATION],
    }

    def __init__(
        self,
        name: str,
        type: ModelType,
        owned_by: str,
        aliases: list[str],
        routing_strategy: str,
        providers: list["BaseModelClient"],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(name=name, type=type, owned_by=owned_by, aliases=aliases, routing_strategy=routing_strategy, providers=providers)

    def get_client(self, endpoint: str) -> "BaseModelClient":
        if endpoint and self.type not in self.ENDPOINT_MODEL_TYPE_TABLE[endpoint]:
            raise WrongModelTypeException()

        if self.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            strategy = RoundRobinRoutingStrategy(self._providers, self._cycle)
        else:  # ROUTER_STRATEGY__SHUFFLE
            strategy = ShuffleRoutingStrategy(self._providers)

        client = strategy.choose_model_client()
        client.endpoint = endpoint

        return client
