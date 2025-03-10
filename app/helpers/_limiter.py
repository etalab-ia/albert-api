import json
import hashlib
from typing import Literal
from limits import RateLimitItemPerDay, RateLimitItemPerMinute, storage, strategies
from sqlalchemy import select

from app.clients.database import RedisDatabaseClient
from app.helpers import AuthManager
from app.sql.models import User as UserTable


class Limiter:
    CACHE_EXPIRATION = 3600 * 24 * 30  # 30 days

    def __init__(self, auth: AuthManager, redis: RedisDatabaseClient, strategy: Literal["moving_window", "fixed_window", "sliding_window"]):
        self.auth = auth
        self.redis = storage.RedisStorage(uri="async+redis://:6379")

        if strategy == "moving_window":
            self.strategy = strategies.MovingWindowRateLimiter(storage=self.redis)
        elif strategy == "fixed_window":
            self.strategy = strategies.FixedWindowRateLimiter(storage=self.redis)
        elif strategy == "sliding_window":
            self.strategy = strategies.SlidingWindowCounterRateLimiter(storage=self.redis)

    def cache(func):
        """
        Decorator to cache the result of a function in Redis.
        """

        async def wrapper(self, *args, **kwargs):
            key = hashlib.sha256(f"{func.__name__}-{args}-{kwargs}".encode()).hexdigest()
            result = self.redis.get(key)
            if result:
                result = json.loads(result)
                return result
            result = func(self)
            self.redis.setex(key, self.CACHE_EXPIRATION, json.dumps(result))

            return result

        return wrapper

    @cache
    async def _get_user_id(self, user: str) -> int:
        async with self.auth.sql.session() as session:
            result = await session.execute(statement=select(UserTable.id).where(UserTable.display_id == user))
            return result.scalar_one().id

    async def __call__(self, user: str, rpd: int, rpm: int) -> None:
        user_id = await self._get_user_id(user=user)

        rpd_limit = RateLimitItemPerDay(amount=rpd, key_for=f"rpd:{user_id}")
        rpm_limit = RateLimitItemPerMinute(amount=rpm, key_for=f"rpm:{user_id}")

        self.strategy.add(rpd_limit)
        self.strategy.add(rpm_limit)
