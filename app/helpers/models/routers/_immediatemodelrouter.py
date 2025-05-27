from app.clients.model import BaseModelClient as ModelClient
from app.helpers.models.routers.strategies import RoundRobinRoutingStrategy, ShuffleRoutingStrategy
from app.schemas.core.models import RoutingStrategy
from app.schemas.models import ModelType
from app.utils.exceptions import WrongModelTypeException
from app.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS, ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS, ENDPOINT__OCR, ENDPOINT__RERANK

from ._basemodelrouter import BaseModelRouter


class ImmediateModelRouter(BaseModelRouter):
    ENDPOINT_MODEL_TYPE_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: [ModelType.AUTOMATIC_SPEECH_RECOGNITION],
        ENDPOINT__CHAT_COMPLETIONS: [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__EMBEDDINGS: [ModelType.TEXT_EMBEDDINGS_INFERENCE],
        ENDPOINT__OCR: [ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__RERANK: [ModelType.TEXT_CLASSIFICATION],
    }

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
        super().__init__(id, type, owned_by, aliases, routing_strategy, clients, *args, **kwargs)

    def get_client(self, endpoint: str) -> ModelClient | None:
        if endpoint and self.type not in self.ENDPOINT_MODEL_TYPE_TABLE[endpoint]:
            raise WrongModelTypeException()

        if self._routing_strategy == RoutingStrategy.ROUND_ROBIN:
            strategy = RoundRobinRoutingStrategy(self._strategy_clients, self._cycle)
        else:  # ROUTER_STRATEGY__SHUFFLE
            strategy = ShuffleRoutingStrategy(self._strategy_clients)

        strategy_client = strategy.choose_model_client()
        client = next(filter(lambda c: c.model == strategy_client.model_name and c.api_url == strategy_client.api_url, self._clients), None)

        if isinstance(client, ModelClient):
            client.endpoint = endpoint

        return client
