import datetime as dt

from grist_api import GristDocAPI
from fastapi import HTTPException
from redis import Redis


class GristKeyManager(GristDocAPI):
    CACHE_EXPIRATION = 3600 # 1h

    def __init__(self, table_id: str, redis_host: str, redis_port: int, redis_password:str=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = kwargs.get("api_key")
        self.doc_id = kwargs.get("doc_id")
        self.table_id = table_id
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis = Redis(host=self.redis_host, port=self.redis_port, password=redis_password)

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

    def redis_cache(func):
        """
        Decorator to cache the result of a function in Redis with a 24h expiration.
        """

        def wrapper(self):
            key = f"auth-{self.doc_id}-{self.table_id}"
            result = self.redis.get(key)
            if result:
                result = result.decode("utf-8").split(":")
                return result
            result = func(self)
            self.redis.set(key, ":".join(result))
            self.redis.expire(key, self.CACHE_EXPIRATION)

            return result

        return wrapper

    @redis_cache
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
