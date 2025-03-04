import traceback

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis

from app.utils.logging import logger


class RedisDatabaseClient(AsyncRedis):
    def __init__(self, *args, **kwargs) -> None:
        """
        RedisDatabaseClient extends AsyncRedis to check if cache is reachable when API startup.
        """
        redis = SyncRedis(**kwargs["connection_pool"].connection_kwargs)
        try:
            redis.ping()
        except Exception:
            logger.debug(msg=traceback.format_exc())
            raise ValueError("Redis database is not reachable.")
        finally:
            redis.close()

        super().__init__(*args, **kwargs)
