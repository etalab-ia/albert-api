from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis


class CacheClient(AsyncRedis):
    def __init__(self, *args, **kwargs) -> None:
        """
        CacheClient extends AsyncRedis to check if cache is reachable when API startup.
        """
        # check if cache is reachable when API startup
        redis = SyncRedis(**kwargs["connection_pool"].connection_kwargs)
        redis.ping()
        redis.close()

        super().__init__(*args, **kwargs)
