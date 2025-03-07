from typing import Literal

from limits import RateLimitItemPerDay, RateLimitItemPerMinute
from limits.aio import storage, strategies
from coredis import ConnectionPool

from app.helpers import AuthManager
from app.schemas.core.auth import AuthenticatedUser
from app.utils.exceptions import RateLimitExceeded


class Limiter:
    CACHE_EXPIRATION = 3600 * 24 * 30  # 30 days

    def __init__(self, auth: AuthManager, connection_pool: ConnectionPool, strategy: Literal["moving_window", "fixed_window", "sliding_window"]):
        self.auth = auth
        self.connection_pool = connection_pool
        self.redis_host = self.connection_pool.connection_kwargs["host"]
        self.redis_port = self.connection_pool.connection_kwargs["port"]
        self.redis_password = self.connection_pool.connection_kwargs.get("password", "")
        self.redis = storage.RedisStorage(
            uri=f"async+redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}",
            connection_pool=self.connection_pool,
        )

        if strategy == "moving_window":
            self.strategy = strategies.MovingWindowRateLimiter(storage=self.redis)
        elif strategy == "fixed_window":
            self.strategy = strategies.FixedWindowRateLimiter(storage=self.redis)
        elif strategy == "sliding_window":
            self.strategy = strategies.SlidingWindowCounterRateLimiter(storage=self.redis)

    async def __call__(self, user: AuthenticatedUser, model: str) -> None:
        # @TODO: add tpm limit
        rpm = user.limits.get(model).rpm
        rpd = user.limits.get(model).rpd

        if rpm:
            rpm_limit = RateLimitItemPerMinute(amount=rpm)
            result = await self.strategy.hit(rpm_limit, f"rpm:{user.id}:{model}")
            if not result:
                raise RateLimitExceeded(detail=f"{str(rpm_limit).split("per")[0]} requests for {model} per minute exceeded.")
        if rpd:
            rpd_limit = RateLimitItemPerDay(amount=rpd)
            result = await self.strategy.hit(rpd_limit, f"rpd:{user.id}:{model}")
            if not result:
                raise RateLimitExceeded(detail=f"{str(rpd_limit).split("per")[0]} requests for {model} per day exceeded.")
