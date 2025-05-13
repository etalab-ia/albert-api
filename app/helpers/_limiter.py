import logging
import traceback
from typing import Optional

from coredis import ConnectionPool
from limits import RateLimitItemPerDay, RateLimitItemPerMinute
from limits.aio import storage, strategies

from app.schemas.auth import LimitType
from app.schemas.core.auth import LimitingStrategy

logger = logging.getLogger(__name__)


class Limiter:
    def __init__(self, connection_pool: ConnectionPool, strategy: LimitingStrategy):
        self.connection_pool = connection_pool
        self.redis_host = self.connection_pool.connection_kwargs.get("host", "localhost")
        self.redis_port = self.connection_pool.connection_kwargs.get("port", 6379)
        self.redis_password = self.connection_pool.connection_kwargs.get("password", "")
        self.redis = storage.RedisStorage(uri=f"async+redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}", connection_pool=self.connection_pool)  # fmt: off

        if strategy == LimitingStrategy.MOVING_WINDOW:
            self.strategy = strategies.MovingWindowRateLimiter(storage=self.redis)
        elif strategy == LimitingStrategy.FIXED_WINDOW:
            self.strategy = strategies.FixedWindowRateLimiter(storage=self.redis)
        else:  # SLIDING_WINDOW
            self.strategy = strategies.SlidingWindowCounterRateLimiter(storage=self.redis)

    async def __call__(self, user_id: int, model: str, type: LimitType, value: Optional[int] = None, hit: bool = True, cost: int = 1) -> bool:
        """
        Check if the user has reached the limit for the given type and model.

        Args:
            user_id(int): The user ID to check the limit for.
            model(str): The model to check the limit for.
            type(LimitType): The type of limit to check.
            value(Optional[int]): The value of the limit. If not provided, the limit will be hit.
            hit(bool): Whether to hit the limit, defaults to True. If hit is True, the limit will be hit by the cost. If hit is False, the limit will not be hit and the remaining limit will be returned.
            cost(int): The cost of the limit, defaults to 1.

        Returns:
            bool: True if the limit has been hit, False otherwise.
        """
        if value is None:
            return True

        try:
            if type == LimitType.TPM:
                limit = RateLimitItemPerMinute(amount=value)
            elif type == LimitType.TPD:
                limit = RateLimitItemPerDay(amount=value)
            elif type == LimitType.RPM:
                limit = RateLimitItemPerMinute(amount=value)
            elif type == LimitType.RPD:
                limit = RateLimitItemPerDay(amount=value)

            if hit:
                result = await self.strategy.hit(limit, f"{type.value}:{user_id}:{model}", cost=cost)
                return result
            else:
                window = await self.strategy.get_window_stats(limit, f"{type.value}:{user_id}:{model}")
                return window.remaining > 0

        except Exception:
            logger.error(msg="Error during rate limit check.")
            logger.error(msg=traceback.format_exc())

        return True
