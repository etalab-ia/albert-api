import base64
import datetime as dt
import hashlib
import json
from typing import Optional
import uuid
from typing import Any, Callable

from grist_api import GristDocAPI
from redis import Redis

from app.schemas.security import Role, User


class AuthenticationClient(GristDocAPI):
    CACHE_EXPIRATION = 3600  # 1h

    def __init__(self, cache: Redis, table_id: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.session_id = str(uuid.uuid4())
        self.table_id = table_id
        self.redis = cache

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
            return User(id=self._api_key_to_user_id(input=key), role=Role[keys[key]["role"]], name=keys[key]["name"])

    def cache(func) -> Callable[..., Any]:
        """
        Decorator to cache the result of a function in Redis.
        """

        def wrapper(self) -> Any:
            key = f"auth-{self.session_id}"
            result = self.redis.get(key)
            if result:
                result = json.loads(result)
                return result
            result = func(self)
            self.redis.setex(key, self.CACHE_EXPIRATION, json.dumps(result))

            return result

        return wrapper

    @cache
    def _get_api_keys(self) -> dict:
        """
        Get all keys from a table in the Grist document.

        Returns:
            dict: dictionary of keys and their corresponding access level
        """
        records = self.fetch_table(table_name=self.table_id)

        keys = dict()
        for record in records:
            if record.EXPIRATION > dt.datetime.now().timestamp():
                keys[record.KEY] = {
                    "id": self._api_key_to_user_id(input=record.KEY),
                    "role": Role.get(name=record.ROLE.upper(), default=Role.USER)._name_,
                    "name": record.USER,
                }

        return keys

    @staticmethod
    def _api_key_to_user_id(input: str) -> str:
        """
        Generate a 16 length unique code from an input string using salted SHA-256 hashing.

        Args:
            input_string (str): The input string to generate the code from.

        Returns:
            tuple[str, bytes]: A tuple containing the generated code and the salt used.
        """
        hash = hashlib.sha256((input).encode()).digest()
        hash = base64.urlsafe_b64encode(hash).decode()
        # remove special characters and limit length
        hash = "".join(c for c in hash if c.isalnum())[:16].lower()

        return hash
