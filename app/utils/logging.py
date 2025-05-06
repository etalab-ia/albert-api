from contextvars import ContextVar
from logging import Filter, Formatter, Logger, StreamHandler, getLogger
import sys
from typing import Optional

from app.utils.settings import settings

client_ip: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)


class ClientIPFilter(Filter):
    def filter(self, record):
        client_addr = client_ip.get()
        record.client_ip = client_addr if client_addr else "."
        return True


def setup_logger() -> Logger:
    logger = getLogger(name="app")
    logger.setLevel(level=settings.general.log_level)
    handler = StreamHandler(stream=sys.stdout)
    formatter = Formatter("[%(asctime)s][%(process)d:%(name)s][%(levelname)s] %(client_ip)s - %(message)s")
    handler.setFormatter(formatter)
    handler.addFilter(ClientIPFilter())

    logger.addHandler(handler)
    logger.propagate = False  # Prevent propagation to root logger

    return logger


logger = setup_logger()
