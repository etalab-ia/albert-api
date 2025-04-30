from app.clients.model import BaseModelClient as ModelClient
from app.helpers._basemodelrouter import BaseModelRouter
from app.schemas.models import ModelType

from app.workers.sender.rpc_client import RPCClient
from app.helpers._metricstracker import MetricsTracker


class QueuingModelRouter(BaseModelRouter):
    def __init__(
        self,
        rpc_client: RPCClient,
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
        self.rpc_client = rpc_client
        self.metrics_tracker = MetricsTracker([client.api_url for client in clients], 2, 30)

    def get_client(self, endpoint: str) -> ModelClient | None:
        # TODO: To implement
        # 1. Call to self.rpc_client.call() to send request to the right queue (one queue per model type) with the params:
        #   a. the caller's priority
        #   b. the routing strategy
        # 2. Wait for message to be processed by consumer
        # 3. Response is received with either a client's info (url, api_key) or None result meaning no client was available
        # 4. Return response as the return object of this method
        return None
