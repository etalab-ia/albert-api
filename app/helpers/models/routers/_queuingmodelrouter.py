from app.clients.model import BaseModelClient as ModelClient
from app.schemas.models import ModelType
from app.helpers.message_producer.rpc_client import RPCClient

from ._basemodelrouter import BaseModelRouter
from ._metricstracker import MetricsTracker


class QueuingModelRouter(BaseModelRouter):
    def __init__(
        self,
        message_producer: RPCClient,
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
        self.message_producer = message_producer
        self.metrics_tracker = MetricsTracker([client.api_url for client in clients], 2, 30)

    def get_client(self, endpoint: str) -> ModelClient | None:
        # TODO: To implement
        # 1. Call to self.message_producer.call() to send request to the right queue (one queue per model router) with the params:
        #   a. the model router id
        #   b. the caller's priority
        # 2. Wait for message to be processed by consumer
        # 3. Response is received with either a client's info (url) or None result meaning no client was available
        # 4. Return client corresponding to the url among the list of ModelClient
        return None
