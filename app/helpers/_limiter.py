from typing import Literal

from limits import RateLimitItemPerDay, RateLimitItemPerMinute
from limits.aio import storage, strategies
from coredis import ConnectionPool

from app.helpers import AuthManager
from app.schemas.core.auth import AuthenticatedUser
from app.schemas.auth import LimitType

from app.utils.logging import logger
import traceback


class Limiter:
    CACHE_EXPIRATION = 3600 * 24 * 30  # 30 days

    def __init__(self, auth: AuthManager, connection_pool: ConnectionPool, strategy: Literal["moving_window", "fixed_window", "sliding_window"]):
        self.auth = auth
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

    async def __call__(self, user: AuthenticatedUser, model: str, type: Literal[LimitType.RPM, LimitType.RPD]) -> None:
        # @TODO: add tpm limit

        try:
            if type == LimitType.RPM and user.limits.get(model).rpm:
                limit = RateLimitItemPerMinute(amount=user.limits.get(model).rpm)
                result = await self.strategy.hit(limit, f"rpm:{user.id}:{model}")
                if not result:
                    return False

            elif type == LimitType.RPD and user.limits.get(model).rpd:
                limit = RateLimitItemPerDay(amount=user.limits.get(model).rpd)
                result = await self.strategy.hit(limit, f"rpd:{user.id}:{model}")
                if not result:
                    return False
        except Exception:
            logger.error(msg="Error during rate limit check.")
            logger.error(msg=traceback.format_exc())

        return True
