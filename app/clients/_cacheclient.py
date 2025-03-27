from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
import logging

from app.utils.settings import settings

logger = logging.getLogger(__name__)


class CacheClient(AsyncRedis):
    VERSION_KEY = "app:cache_version"

    def __init__(self, *args, **kwargs) -> None:
        """
        CacheClient extends AsyncRedis to check if cache is reachable when API startup
        and implements version-based cache invalidation.
        """
        # Get current app version from settings
        app_version = settings.app_version

        # Check if cache is reachable when API startup
        sync_redis = SyncRedis(**kwargs["connection_pool"].connection_kwargs)
        sync_redis.ping()

        # Check cached version and flush if needed
        stored_version = sync_redis.get(self.VERSION_KEY)
        if stored_version:
            stored_version = stored_version.decode("utf-8")

        if not stored_version or stored_version != app_version:
            logger.info(f"Cache version mismatch. Stored: {stored_version}, Current: {app_version}. Flushing cache.")
            sync_redis.flushall()
            sync_redis.set(self.VERSION_KEY, app_version)
            logger.info(f"Cache flushed and version updated to {app_version}")
        else:
            logger.info(f"Cache version match: {app_version}. Using existing cache.")

        sync_redis.close()
        super().__init__(*args, **kwargs)
