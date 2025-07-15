"""
pika (="RabbitMQ") connections and channels are not thread safe, and not made to be used by multiple threads.
Thus, anytime a thread needs one, it creates its own.
This seems to be the worst option possible, though it might be the only one available.
TODO: maybe a dedicated thread, wrapped in a class with locks?
Consumers need their own channel to run in a separated thread though.
"""
import pika

# TODO: use settings to adapt to the configuration
_credentials = pika.PlainCredentials('master', 'changeme')
_parameters = pika.ConnectionParameters('localhost', 5672, '/', _credentials)


# TODO refactor this to avoid confusion

def get_rabbitmq_connection():
    return pika.BlockingConnection(_parameters)

def get_rabbitmq_channel():
    return get_rabbitmq_connection().channel()


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
