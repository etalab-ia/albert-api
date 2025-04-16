import random

from app.clients.model import BaseModelClient as ModelClient
from app.helpers._basemodelrouter import BaseModelRouter
from app.schemas.core.models import RoutingStrategy
from app.schemas.models import ModelType
from app.schemas.core.settings import Model as ModelSettings
from app.utils.exceptions import WrongModelTypeException
from app.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS, ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS, ENDPOINT__OCR, ENDPOINT__RERANK


class ModelRouter(BaseModelRouter):
    ENDPOINT_MODEL_TYPE_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: [ModelType.AUTOMATIC_SPEECH_RECOGNITION],
        ENDPOINT__CHAT_COMPLETIONS: [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__EMBEDDINGS: [ModelType.TEXT_EMBEDDINGS_INFERENCE],
        ENDPOINT__OCR: [ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__RERANK: [ModelType.TEXT_CLASSIFICATION],
    }

    def __init__(
        self, id: str, type: ModelType, owned_by: str, aliases: list[str], routing_strategy: str, clients: list[ModelSettings], *args, **kwargs
    ) -> None:
        super().__init__(id, type, owned_by, aliases, routing_strategy, clients, *args, **kwargs)

    def get_client(self, endpoint: str) -> ModelClient:
        if endpoint and self.type not in self.ENDPOINT_MODEL_TYPE_TABLE[endpoint]:
            raise WrongModelTypeException()

        if self._routing_strategy == RoutingStrategy.ROUND_ROBIN:
            client = self._routing_strategy_round_robin()
        else:  # ROUTER_STRATEGY__SHUFFLE
            client = self._routing_strategy_shuffle()

        client.endpoint = endpoint

        return client

    def _routing_strategy_shuffle(self) -> ModelClient:
        return random.choice(self._clients)

    def _routing_strategy_round_robin(self) -> ModelClient:
        return next(self._cycle)
