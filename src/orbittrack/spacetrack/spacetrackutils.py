import functools
from typing import Callable

from limits import RateLimitItem, parse
from limits.storage import (
    MemcachedStorage,
    MemoryStorage,
    MongoDBStorage,
    RedisClusterStorage,
    RedisSentinelStorage,
    RedisStorage,
)
from limits.strategies import (
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
    SlidingWindowCounterRateLimiter,
)

from orbittrack.spacetrack.exceptions import (
    SpaceTrackRateLimitError,
    SpaceTrackRateLimitExceededError,
)


class SpaceTrackUtils:
    """
    Utility class providing decorators for authentication and resource management
    for SpaceTrack API client methods.
    """

    # Shared storage and limiter for all decorated methods
    _ratelimit_storage = MemoryStorage()
    _ratelimit_limiter = MovingWindowRateLimiter(_ratelimit_storage)
    _hourly_rate_limit = parse("300/hour")
    _minute_rate_limit = parse("30/minute")

    @classmethod
    def get_minute_rate_limit(cls) -> RateLimitItem:
        return cls._minute_rate_limit

    @classmethod
    def get_hourly_rate_limit(cls) -> RateLimitItem:
        return cls._hourly_rate_limit

    @classmethod
    def set_minute_rate_limit(cls, provided_limit: RateLimitItem) -> None:
        """
        Sets the minute rate limit for the SpaceTrack API.
        If the provided limit exceeds the default, raises an error.
        """
        default_limit = cls._minute_rate_limit
        if (
            provided_limit.amount / provided_limit.GRANULARITY.seconds
            > default_limit.amount / default_limit.GRANULARITY.seconds
        ):
            raise SpaceTrackRateLimitExceededError(
                "This rate limit exceeds the default allowed limit."
            )
        else:
            cls._minute_rate_limit = provided_limit

    @classmethod
    def set_hourly_rate_limit(cls, provided_limit: RateLimitItem) -> None:
        """
        Sets the hourly rate limit for the SpaceTrack API.
        If the provided limit exceeds the default, raises an error.
        """
        default_limit = cls._hourly_rate_limit
        if (
            provided_limit.amount / provided_limit.GRANULARITY.seconds
            > default_limit.amount / default_limit.GRANULARITY.seconds
        ):
            raise SpaceTrackRateLimitExceededError(
                "This rate limit exceeds the default allowed limit."
            )
        else:
            cls._hourly_rate_limit = provided_limit

    @classmethod
    def set_ratelimiter(
        cls,
        ratelimiter: MovingWindowRateLimiter
        | FixedWindowRateLimiter
        | SlidingWindowCounterRateLimiter,
    ) -> None:
        """
        Sets the rate limiter for the SpaceTrack API.
        """
        cls._ratelimit_limiter = ratelimiter

    @classmethod
    def set_ratelimit_storage(
        cls,
        storage: MemoryStorage
        | MemcachedStorage
        | MongoDBStorage
        | RedisClusterStorage
        | RedisStorage
        | RedisSentinelStorage,
    ) -> None:
        """
        Sets the storage backend for the rate limiter.
        """
        cls._ratelimit_storage = storage

    @classmethod
    def _ensure_limiter(cls) -> None:
        if cls._ratelimit_storage is None or cls._ratelimit_limiter is None:
            cls._ratelimit_storage = MemoryStorage()
            cls._ratelimit_limiter = MovingWindowRateLimiter(cls._ratelimit_storage)

    @staticmethod
    def ratelimit(func: Callable) -> Callable:
        """
        Decorator to apply rate limiting to SpaceTrack API client methods.
        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):  # type: ignore
            SpaceTrackUtils._ensure_limiter()
            limiter = SpaceTrackUtils._ratelimit_limiter
            minute_rate_limit = SpaceTrackUtils._minute_rate_limit
            hourly_rate_limit = SpaceTrackUtils._hourly_rate_limit
            if not limiter.hit(minute_rate_limit, "space_track_minute"):
                raise SpaceTrackRateLimitError("Minute rate limit exceeded")
            if not limiter.hit(hourly_rate_limit, "space_track_hourly"):
                raise SpaceTrackRateLimitError("Hourly rate limit exceeded")

            return func(self, *args, **kwargs)

        return wrapper

    @staticmethod
    def handle_login_and_logout(func: Callable) -> Callable:
        """
        Decorator to handle login and logout for SpaceTrack API client methods.
        Ensures the client is authenticated before making requests.
        """

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):  # type: ignore
            if not self.authenticated:
                await self.login()
            result = await func(self, *args, **kwargs)
            if self.authenticated:
                await self.close()
            return result

        return wrapper
