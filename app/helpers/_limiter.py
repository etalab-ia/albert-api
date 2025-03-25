from typing import Literal, Optional

from limits import RateLimitItemPerDay, RateLimitItemPerMinute
from limits.aio import storage, strategies
from coredis import ConnectionPool

from app.schemas.auth import LimitType

from app.utils.logging import logger
import traceback


class Limiter:
    CACHE_EXPIRATION = 3600 * 24 * 30  # 30 days

    def __init__(self, connection_pool: ConnectionPool, strategy: Literal["moving_window", "fixed_window", "sliding_window"]):
        self.connection_pool = connection_pool
        self.redis_host = self.connection_pool.connection_kwargs["host"]
        self.redis_port = self.connection_pool.connection_kwargs["port"]
        self.redis_password = self.connection_pool.connection_kwargs.get("password", "")
        self.redis = storage.RedisStorage(uri=f"async+redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}", connection_pool=self.connection_pool)  # fmt: off

        if strategy == "moving_window":
            self.strategy = strategies.MovingWindowRateLimiter(storage=self.redis)
        elif strategy == "fixed_window":
            self.strategy = strategies.FixedWindowRateLimiter(storage=self.redis)
        elif strategy == "sliding_window":
            self.strategy = strategies.SlidingWindowCounterRateLimiter(storage=self.redis)

    async def __call__(self, user_id: int, model: str, type: Literal[LimitType.RPM, LimitType.RPD], value: Optional[int] = None) -> None:
        # @TODO: add tpm limit

        try:
            if type == LimitType.RPM and value is not None:
                limit = RateLimitItemPerMinute(amount=value)
                result = await self.strategy.hit(limit, f"rpm:{user_id}:{model}")
                if not result:
                    return False

            elif type == LimitType.RPD and value is not None:
                limit = RateLimitItemPerDay(amount=value)
                result = await self.strategy.hit(limit, f"rpd:{user_id}:{model}")
                if not result:
                    return False
        except Exception:
            logger.error(msg="Error during rate limit check.")
            logger.error(msg=traceback.format_exc())

        return True
