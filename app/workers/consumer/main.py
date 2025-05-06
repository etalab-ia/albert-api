from itertools import cycle
import logging

from app.helpers.strategies.roundrobinmodelclientselectionstrategy import RoundRobinModelClientSelectionStrategy
from app.helpers.strategies.shufflemodelclientselectionstrategy import ShuffleModelClientSelectionStrategy
from app.helpers.strategies.leastbusymodelclientselectionstrategy import LeastBusyModelClientSelectionStrategy
from app.schemas.core.models import RoutingStrategy
from app.utils.settings import settings
from app.workers.consumer.rpc_server import RPCServer


async def main_consumer(p_rpc_server: RPCServer):
    pass


def shutdown():
    pass


if __name__ == "__main__":
    # Create one RPCServer instance for all ModelRouter instances
    logging.info("Starting consumer")

    strategies = {}
    for model in settings.models:
        if model.enable_queueing:
            client_urls = [client.api_url for client in model.clients]
            if model.routing_strategy == RoutingStrategy.LEAST_BUSY:
                strategy = LeastBusyModelClientSelectionStrategy(client_urls)
            elif model.routing_strategy == RoutingStrategy.ROUND_ROBIN:
                strategy = RoundRobinModelClientSelectionStrategy(client_urls, cycle(client_urls))
            else:
                strategy = ShuffleModelClientSelectionStrategy(client_urls)
            strategies[model.id] = strategy

    rpc_server = RPCServer(settings.RABBITMQ_URL, strategies)

    # TODO: create an asyncio loop and add tracker to least busy strategy
