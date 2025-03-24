from contextvars import ContextVar
import logging
from logging import Logger
import sys
from typing import Optional

from app.utils.settings import settings

client_ip: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)


class ClientIPFilter(logging.Filter):
    def filter(self, record):
        client_addr = client_ip.get()
        record.client_ip = client_addr if client_addr else "."
        return True


def setup_logger() -> Logger:
    logger = logging.getLogger(name="app")
    logger.setLevel(level=settings.log_level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s][%(process)d:%(threadName)s][%(levelname)s] %(client_ip)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addFilter(ClientIPFilter())
    logger.addHandler(handler)

    return logger


logger = setup_logger()
