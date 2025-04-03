import base64
from collections import namedtuple
import datetime as dt
import hashlib
import json
import traceback
from typing import List, Optional

import aiohttp
from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
import requests

from app.schemas.security import Role, User
from app.utils.logging import logger


class AsyncGristDocAPI:
    def __init__(self, doc_id: str, server: str, api_key: str):
        self.doc_id = doc_id
        self.server = server
        self.api_key = api_key
        self.base_url = f"{server}/api"

    async def _request(self, method: str, endpoint: str, data: Optional[dict] = None):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with aiohttp.ClientSession() as session:
            if method in ["GET"]:
                data = {"params": data}
            else:
                headers["Content-Type"] = "application/json"
                data = {"json": data}

            async with session.request(method, f"{self.base_url}{endpoint}", headers=headers, **data) as response:
                response.raise_for_status()
                return await response.json()

    def ping(self):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        endpoint = "/orgs"

        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
            return response.status_code == 200
        except Exception as e:
            return False

    async def fetch_table(self, table_name: str, filter: Optional[dict] = None, limit: int = 0) -> List[namedtuple]:
        endpoint = f"/docs/{self.doc_id}/tables/{table_name}/records"
        data = {"filter": json.dumps(filter), "limit": limit} if filter else {"limit": limit}
        results = await self._request(method="GET", endpoint=endpoint, data=data)
        results = [dict(id=result["id"], **result["fields"]) for result in results["records"]]
        return [namedtuple(table_name, result.keys())(**result) for result in results]

    async def update_records(self, table_name: str, record_dicts: List[dict]):
        endpoint = f"/docs/{self.doc_id}/tables/{table_name}/records"
        data = {"records": [{"id": record.pop("id"), "fields": record} for record in record_dicts]}
        result = await self._request(method="PATCH", endpoint=endpoint, data=data)
        return result


class AuthenticationClient(AsyncGristDocAPI):
    CACHE_EXPIRATION = 172800  # 48h

    class GristRecord(BaseModel):
        ID2: Optional[str] = None
        ROLE: str = Role.USER
        EXPIRATION: int = dt.datetime.now().timestamp()
        KEY: Optional[str] = "EMPTY"
        USER: Optional[str] = ""

        class Config:
            extra = "allow"

    def __init__(self, cache: Redis, table_id: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        assert self.ping(), "Grist is not reachable"
        self.table_id = table_id
        self.redis = cache

        # @TODO: check columns exists in Grist

    async def check_api_key(self, key: str) -> Optional[User]:
        """
        Get API key details from cache or Grist and return a User object.

        Args:
            key (str): API key to look up

        Returns:
            Optional[User]: User object if found, None otherwise
        """
        user_id = self.api_key_to_user_id(input=key)
        ttl = -2

        # fetch from Redis
        redis_key = f"{self.table_id}_{user_id}"
        cache_user = await self.redis.get(redis_key)

        if cache_user:
            cache_user = json.loads(cache_user)
            try:
                user = User(id=cache_user["id"], role=Role.get(cache_user["role"]), name=cache_user.get("name"))
                ttl = await self.redis.ttl(redis_key)
                if ttl > 300:
                    return user
            except ValidationError as e:
                logger.warning(msg="Invalid User in cache: %s" % e)

        try:
            # fetch from grist
            records = await self.fetch_table(table_name=self.table_id, filter={"KEY": [key]}, limit=1)
            if not records:  # invalid api key
                return

            record = self.GristRecord(**records[0]._asdict())
            if record.ID2 != user_id:
                record.ID2 = user_id
                await self.update_records(table_name=self.table_id, record_dicts=[record.model_dump()])

            if record.KEY == key and record.EXPIRATION > dt.datetime.now().timestamp():
                cache_user = {"id": record.ID2, "role": Role.get(name=record.ROLE.upper(), default=Role.USER)._name_, "name": record.USER}
                await self.redis.setex(redis_key, self.CACHE_EXPIRATION, json.dumps(cache_user))
                user = User(id=cache_user["id"], role=Role.get(cache_user["role"]), name=cache_user.get("name"))
                return user

        except Exception as e:
            logger.error(msg="Error fetching user from Grist")
            logger.debug(msg=traceback.format_exc())
            if ttl > -2:
                logger.info(msg="Recovery user auth from cache.")
                await self.redis.setex(redis_key, self.CACHE_EXPIRATION, json.dumps(cache_user))
                return user

    @staticmethod
    def api_key_to_user_id(input: str) -> str:
        """
        Generate a 16 length unique user id from an input string using SHA-256 hashing.

        Args:
            input_string (str): The input string to generate the user id from.

        Returns:
            str: The generated user id.
        """
        hash = hashlib.sha256((input).encode()).digest()
        hash = base64.urlsafe_b64encode(hash).decode()
        # remove special characters and limit length
        hash = "".join(c for c in hash if c.isalnum())[:16].lower()

        return hash
