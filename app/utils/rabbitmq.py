"""
pika (="RabbitMQ") connections and channels are not thread safe, and not made to be used by multiple threads.
Thus, anytime a thread needs one, it creates its own.
This seems to be the worst option possible, though it might be the only one available.
TODO: maybe a dedicated thread, wrapped in a class with locks?
Consumers need their own channel to run in a separated thread though.
"""
import pika
import aio_pika
import asyncio
from app.utils.configuration import configuration

rmq_config = configuration.dependencies.rabbitmq

if rmq_config:
    _credentials = pika.PlainCredentials(configuration.settings.auth_master_username, configuration.settings.auth_master_key)
    _parameters = pika.ConnectionParameters(rmq_config.host, rmq_config.port, '/', _credentials)


class SenderRabbitMQConnection:

    def __init__(self):
        self.connection = None
        self.channel = None

    def __enter__(self):
        self.connection = pika.BlockingConnection(parameters=_parameters)
        self.channel = self.connection.channel()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.channel:
            self.channel.close()

        if self.connection:
            self.connection.close()


class ConsumerRabbitMQConnection:

    def __init__(self):
        self.connection = pika.BlockingConnection(parameters=_parameters)
        self.channel = self.connection.channel()


class AsyncRabbitMQConnection:

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
        self.connection = await aio_pika.connect_robust(
            host=rmq_config.host,
            port=rmq_config.port,
            login=configuration.settings.auth_master_username,
            password=configuration.settings.auth_master_key,
        )

        self.sender_loop = asyncio.get_running_loop()  # FastAPI event loop

        self.sender_pool = aio_pika.pool.Pool(
            self.connection.channel,
            max_size=100,  # TODO config parameter?
            loop=self.sender_loop
        )

        self.consumer_loop = asyncio.get_running_loop() # FastAPI event loop

        # If using dedicated event loop, they need to be started

    async def publish_default_exchange(self, routing_key: str, message: aio_pika.Message):

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
        await self.connection.close()
        # Careful if using dedicated loop, shutdown needed here
