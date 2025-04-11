from contextvars import ContextVar
from logging import Logger, Filter, getLogger, StreamHandler, Formatter
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
    formatter = Formatter("[%(asctime)s][%(process)d:%(threadName)s][%(levelname)s] %(client_ip)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addFilter(ClientIPFilter())
    logger.addHandler(handler)

    return logger


logger = setup_logger()
