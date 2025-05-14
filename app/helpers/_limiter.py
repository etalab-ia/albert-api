import logging
import traceback
from typing import Optional

import tiktoken
from coredis import ConnectionPool
from limits import RateLimitItemPerDay, RateLimitItemPerMinute
from limits.aio import storage, strategies

from app.schemas.auth import LimitType
from app.schemas.core.auth import LimitingStrategy
from app.schemas.core.settings import LimitsTokenizer

logger = logging.getLogger(__name__)


class Limiter:
    def __init__(self, connection_pool: ConnectionPool, strategy: LimitingStrategy, tokenizer: LimitsTokenizer):
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

        self.tokenizer = self._get_tokenizer(tokenizer)

    @staticmethod
    def _get_tokenizer(tokenizer: LimitsTokenizer):
        if tokenizer == LimitsTokenizer.TIKTOKEN_O200K_BASE:
            return tiktoken.get_encoding("o200k_base")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_P50K_BASE:
            return tiktoken.get_encoding("p50k_base")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_R50K_BASE:
            return tiktoken.get_encoding("r50k_base")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_P50K_EDIT:
            return tiktoken.get_encoding("p50k_edit")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_CL100K_BASE:
            return tiktoken.get_encoding("cl100k_base")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_GPT2:
            return tiktoken.get_encoding("gpt2")

    async def hit(self, user_id: int, model: str, type: LimitType, value: Optional[int] = None, cost: int = 1) -> Optional[bool]:
        """
        Check if the user has reached the limit for the given type and model.

        Args:
            user_id(int): The user ID to check the limit for.
            model(str): The model to check the limit for.
            type(LimitType): The type of limit to check.
            value(Optional[int]): The value of the limit. If not provided, the limit will be hit.
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

            result = await self.strategy.hit(limit, f"{type.value}:{user_id}:{model}", cost=cost)
            return result

        except Exception:
            logger.error(msg="Error during rate limit hit.")
            logger.error(msg=traceback.format_exc())

        return True

    async def remaining(self, user_id: int, model: str, type: LimitType, value: Optional[int] = None) -> Optional[int]:
        if value is None:
            return None

        try:
            if type == LimitType.TPM:
                limit = RateLimitItemPerMinute(amount=value)
            elif type == LimitType.TPD:
                limit = RateLimitItemPerDay(amount=value)
            elif type == LimitType.RPM:
                limit = RateLimitItemPerMinute(amount=value)
            elif type == LimitType.RPD:
                limit = RateLimitItemPerDay(amount=value)

            window = await self.strategy.get_window_stats(limit, f"{type.value}:{user_id}:{model}")
            return window.remaining

        except Exception:
            logger.error(msg="Error during rate limit remaining.")
            logger.error(msg=traceback.format_exc())
