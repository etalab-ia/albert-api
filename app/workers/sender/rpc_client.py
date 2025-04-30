class RPCClient:
    # Connect sender to message broker
    async def first_connect(self) -> None:
        # TODO: To implement
        pass

    async def check_connection(self) -> bool:
        # TODO: To implement
        return False

    # Close RPC connection
    async def close(self) -> None:
        # TODO: To implement
        pass

    # Receives message from broker
    async def on_response(self, message) -> None:
        # TODO: To implement
        pass

    async def call(self, priority: int, threshold: int, model: str):
        # TODO: To implement
        pass
