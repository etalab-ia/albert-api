from functools import lru_cache

from app.schemas.core.configuration import Configuration


@lru_cache
def get_configuration() -> Configuration:
    return Configuration()


configuration = get_configuration()
