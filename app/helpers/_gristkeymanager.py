import datetime as dt
from fastapi import HTTPException
from grist_api import GristDocAPI
from redis import Redis


class GristKeyManager(GristDocAPI):
    CACHE_EXPIRATION = 3600  # 1h

    def __init__(self, table_id: str, redis: Redis, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.get("user")
        self.doc_id = kwargs.get("doc_id")
        self.table_id = table_id
        self.redis = redis

    def check_api_key(self, key: str):
        """
        Check if a key exists in a table of the Grist document.

        Args:
            key (str): key to check
        """
        keys = self._get_api_keys()
        if key in keys:
            return True

        return False

    def cache(func):
        """
        Decorator to cache the result of a function in Redis.
        """

        def wrapper(self):
            key = f"auth-{self.doc_id}-{self.table_id}"
            result = self.redis.get(key)
            if result:
                result = result.decode("utf-8").split(":")
                return result
            result = func(self)
            self.redis.setex(key, self.CACHE_EXPIRATION, ":".join(result))

            return result

        return wrapper

    @cache
    def _get_api_keys(self):
        """
        Get all keys from a table in the Grist document.
        """
        records = self.fetch_table(self.table_id)

        keys = []
        for record in records:
            try:
                if record.EXPIRATION:
                    if record.EXPIRATION > dt.datetime.now().timestamp():
                        keys.append(record.KEY)
                else:
                    keys.append(record.KEY)  # key without expiration
            except AttributeError:
                raise HTTPException(status_code=500, detail="Invalid Grist table schema")

        return keys
