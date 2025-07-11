from contextvars import ContextVar
from logging import Filter, Formatter, Logger, StreamHandler, getLogger
import sys
from typing import Optional

from app.utils.configuration import configuration

client_ip: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)


class ClientIPFilter(Filter):
    def filter(self, record):
        client_addr = client_ip.get()
        record.client_ip = client_addr if client_addr else "."
        return True


def init_logger(name) -> Logger:
    logger = getLogger(name=name)
    logger.setLevel(level=configuration.settings.log_level)
    handler = StreamHandler(stream=sys.stdout)
    formatter = Formatter(configuration.settings.log_format)
    handler.setFormatter(formatter)
    handler.addFilter(ClientIPFilter())

    logger.addHandler(handler)
    logger.propagate = False  # Prevent propagation to root logger

    return logger
