from itertools import cycle
import time

from app.clients.model import BaseModelClient as ModelClient
from app.helpers.models.routers.strategies import RoundRobinRoutingStrategy, ShuffleRoutingStrategy
from app.schemas.core.models import RoutingStrategy
from app.schemas.core.settings import Model as ModelSettings
from app.schemas.models import ModelType
from app.utils.exceptions import WrongModelTypeException
from app.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS, ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS, ENDPOINT__OCR, ENDPOINT__RERANK


class ModelRouter:
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
        clients: list[ModelSettings],
        *args,
        **kwargs,
    ):
        vector_sizes, max_context_lengths = list(), list()

        for client in clients:
            vector_sizes.append(client.vector_size)
            max_context_lengths.append(client.max_context_length)
        # consistency checks
        assert len(set(vector_sizes)) < 2, "All embeddings models in the same model group must have the same vector size."

        # if there are several models with different max_context_length, it will return the minimal value for consistency of /v1/models response
        max_context_lengths = [value for value in max_context_lengths if value is not None]
        max_context_length = min(max_context_lengths) if max_context_lengths else None

        # set attributes of the model (return by /v1/models endpoint)
        self.id = id
        self.type = type
        self.owned_by = owned_by
        self.created = round(time.time())
        self.aliases = aliases
        self.max_context_length = max_context_length

        self._vector_size = vector_sizes[0]
        self._routing_strategy = routing_strategy
        self._cycle = cycle(clients)
        self._clients = clients

    def get_client(self, endpoint: str) -> ModelClient:
        if endpoint and self.type not in self.ENDPOINT_MODEL_TYPE_TABLE[endpoint]:
            raise WrongModelTypeException()

        if self._routing_strategy == RoutingStrategy.ROUND_ROBIN:
            strategy = RoundRobinRoutingStrategy(self._clients, self._cycle)
        else:  # ROUTER_STRATEGY__SHUFFLE
            strategy = ShuffleRoutingStrategy(self._clients)

        client = strategy.choose_model_client()

        return client
