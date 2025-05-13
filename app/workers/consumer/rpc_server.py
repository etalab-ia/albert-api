import logging

from app.helpers.strategies import BaseModelClientSelectionStrategy


class RPCServer:
    def __init__(self, message_broker_url: str, strategies: {str: BaseModelClientSelectionStrategy}) -> None:
        self.message_broker_url = message_broker_url
        self.strategies = strategies  # Key: model router id, Value: strategy instance
        self.connection = None  # Instance of aio_pika AbstractConnection
        self.channel = None  # Instance of aio_pika AbstractChannel
        self.queues = {}  # Key: model router id, Value: aio_pika AbstractQueue instance

    # Connect sender to message broker
    async def first_connect(self) -> None:
        # TODO: To implement
        # Create as many queues as model type
        pass

    async def check_connection(self) -> bool:
        # TODO: To implement
        return False

    # Close RPC connection
    async def close(self) -> None:
        # TODO: To implement
        pass

    # On reception of message from sender, call strategy.choose_model_client()
    def create_model_callback(self, model_router_id):
        async def on_message_callback(message):
            logging.debug("Message consumed on queue %s", model_router_id)

            # Get model client through corresponding strategy
            model_client = self.strategies[model_router_id].choose_model_client()
            client_params = {"clientUrl": model_client.api_url}

            # TODO: reply to sender with the model client's information
