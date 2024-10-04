import datetime as dt
from typing import Optional

from grist_api import GristDocAPI
from redis import Redis
import json
from app.utils.variables import USER_ROLE


# @TODO: change name of the class
class GristKeyManager(GristDocAPI):
    CACHE_EXPIRATION = 3600  # 1h

    def __init__(self, table_id: str, redis: Redis, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.get("user")
        self.doc_id = kwargs.get("doc_id")
        self.table_id = table_id
        self.redis = redis

    def check_api_key(self, key: str) -> Optional[str]:
        """
        Check if a key exists in a table of the Grist document.

        Args:
            key (str): key to check

        Returns:
            Optional[str]: role of the key if it exists, None otherwise
        """
        keys = self._get_api_keys()
        if key in keys:
            return keys[key]

    def cache(func):
        """
        Decorator to cache the result of a function in Redis.
        """

        def wrapper(self):
            key = f"auth-{self.doc_id}-{self.table_id}"
            result = self.redis.get(key)
            if result:
                result = json.loads(result)
                return result
            result = func(self)
            self.redis.setex(key, self.CACHE_EXPIRATION, json.dumps(result))

            return result

        return wrapper

    @cache
    def _get_api_keys(self):
        """
        Get all keys from a table in the Grist document.
        """
        records = self.fetch_table(self.table_id)

        keys = dict()
        for record in records:
            if record.EXPIRATION > dt.datetime.now().timestamp():
                keys[record.KEY] = record.ROLE or USER_ROLE

        return keys
