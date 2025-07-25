import aio_pika
import asyncio
from app.utils.configuration import configuration

rmq_config = configuration.dependencies.rabbitmq


class AsyncRabbitMQConnection:
    """
    This class represents the link between the API and RabbitMQ.
    It is a singleton, as we only open one (robust) connection.
    """

    # Singleton pattern
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AsyncRabbitMQConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):  # Call init once
            return

        self.connection = None

        # To send request down to Router and then clients, we use a pool of channels,
        # as they are only sending one message.
        self.sender_pool = None
        self.sender_loop = None

        self.consumer_loop = None

        # Call init once
        self._initialized = True

    async def setup(self):
        """
        Sets up the AMQP connection to RabbitMQ, and initializes the pools.
        """
        self.connection = await aio_pika.connect_robust(
            host=rmq_config.host,
            port=rmq_config.port,
            login=configuration.settings.auth_master_username,
            password=configuration.settings.auth_master_key,
        )

        self.sender_loop = asyncio.get_running_loop()  # FastAPI event loop

        self.sender_pool = aio_pika.pool.Pool(
            self.connection.channel,
            max_size=rmq_config.sender_pool_size,
            loop=self.sender_loop
        )

        self.consumer_loop = asyncio.get_running_loop() # FastAPI event loop

        # If using dedicated event loop, they need to be started

    async def publish_default_exchange(self, routing_key: str, message: aio_pika.Message):
        """
        Sends a message, to the default exchange.

        Args:
            routing_key(str): The key that represents the targeted queue.
            message(aio_pika.Message): The message to send.
        """
        async def do_publish():
            async with self.sender_pool.acquire() as channel:
                ex = channel.default_exchange
                await ex.publish(
                    message,
                    routing_key=routing_key
                )

        # self.loop.call_soon_threadsafe(lambda: self.loop.create_task(do_publish()))
        self.sender_loop.create_task(do_publish())

    async def close(self):
        """
        Close AMQP connection.
        """
        await self.connection.close()
        # Careful if using dedicated loop, shutdown needed here
