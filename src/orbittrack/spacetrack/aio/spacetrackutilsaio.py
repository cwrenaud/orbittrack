import functools
from typing import Callable
from limits import parse, RateLimitItem
from limits.aio.strategies import (
    MovingWindowRateLimiter as AsyncMovingWindowRateLimiter,
    FixedWindowRateLimiter as AsyncFixedWindowRateLimiter,
    SlidingWindowCounterRateLimiter as AsyncSlidingWindowCounterRateLimiter
)
from limits.aio.storage import (
    MemcachedStorage as AsyncMemcachedStorage,
    MongoDBStorage as AsyncMongoDBStorage,
    RedisClusterStorage as AsyncRedisClusterStorage,
    RedisStorage as AsyncRedisStorage,
    RedisSentinelStorage as AsyncRedisSentinelStorage,
    MemoryStorage as AsyncMemoryStorage,
)
from orbittrack.spacetrack.exceptions import (
    SpaceTrackAuthenticationError,
    SpaceTrackRateLimitError,
    SpaceTrackRateLimitExceededError
)


class AsyncSpaceTrackUtils:
    """
    Utility class providing decorators for authentication and resource management
    for SpaceTrack API client methods.
    """

    # Shared async storage and limiter for all decorated methods
    _ratelimit_storage = None
    _ratelimit_limiter = None
    _hourly_rate_limit = parse("300/hour")
    _minute_rate_limit = parse("30/minute")
    
    
    @classmethod
    def get_minute_rate_limit(cls) -> RateLimitItem:
        """
        Returns the minute rate limit for the SpaceTrack API.
        """
        return cls._minute_rate_limit

    @classmethod
    def get_hourly_rate_limit(cls) -> RateLimitItem:
        """
        Returns the hourly rate limit for the SpaceTrack API.
        """
        return cls._hourly_rate_limit
    
    @classmethod
    def set_minute_rate_limit(cls, provided_limit: RateLimitItem):
        """
        Sets the minute rate limit for the SpaceTrack API.
        If the provided limit exceeds the default, raises an error.
        """
        default_limit = cls._minute_rate_limit
        if (
            provided_limit.amount / provided_limit.GRANULARITY.seconds >
            default_limit.amount / default_limit.GRANULARITY.seconds
        ):
            raise SpaceTrackRateLimitExceededError(
                "This rate limit exceeds the default allowed limit."
            )
        else:
            cls._minute_rate_limit = provided_limit
            
    @classmethod
    def set_hourly_rate_limit(cls, provided_limit: RateLimitItem):
        """
        Sets the hourly rate limit for the SpaceTrack API.
        If the provided limit exceeds the default, raises an error.
        """
        default_limit = cls._hourly_rate_limit
        if (
            provided_limit.amount / provided_limit.GRANULARITY.seconds >
            default_limit.amount / default_limit.GRANULARITY.seconds
        ):
            raise SpaceTrackRateLimitExceededError(
                "This rate limit exceeds the default allowed limit."
            )
        else:
            cls._hourly_rate_limit = provided_limit
            
    @classmethod
    def set_ratelimiter(
        cls,
        ratelimiter: AsyncMovingWindowRateLimiter | AsyncFixedWindowRateLimiter | 
        AsyncSlidingWindowCounterRateLimiter
        ) -> None:
        """
        Sets the rate limiter for the SpaceTrack API.
        """
        cls._ratelimit_limiter = ratelimiter
        
    @classmethod
    def set_ratelimit_storage(
        cls,
        storage: AsyncMemoryStorage | AsyncMemcachedStorage | AsyncMongoDBStorage |
        AsyncRedisClusterStorage | AsyncRedisStorage | AsyncRedisSentinelStorage
    ) -> None:
        """
        Sets the storage backend for the rate limiter.
        """
        cls._ratelimit_storage = storage

    @classmethod
    async def _ensure_limiter(cls):
        if cls._ratelimit_storage is None or cls._ratelimit_limiter is None:
            cls._ratelimit_storage = AsyncMemoryStorage()
            cls._ratelimit_limiter = AsyncMovingWindowRateLimiter(
                cls._ratelimit_storage
            )

    @staticmethod
    def ratelimit(func: Callable) -> Callable:
        """
        Decorator to apply rate limiting to SpaceTrack API client methods.
        Uses a moving window rate limiter with a memory storage backend.
        """

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            await AsyncSpaceTrackUtils._ensure_limiter()
            limiter = AsyncSpaceTrackUtils._ratelimit_limiter
            minute_rate_limit = AsyncSpaceTrackUtils._minute_rate_limit
            hourly_rate_limit = AsyncSpaceTrackUtils._hourly_rate_limit
            if limiter is None:
                raise RuntimeError("Rate limiter was not properly initialized.")
            if (
                not await limiter.hit(minute_rate_limit, "space_track_api") and
                not await limiter.hit(hourly_rate_limit, "space_track_api")
            ):
                raise SpaceTrackRateLimitError(
                    "Rate limit exceeded. Please try again later."
                )
            return await func(self, *args, **kwargs)

        return wrapper

    @staticmethod
    def handle_login(func):
        """
        Decorator to ensure the user is logged in before making an API call.
        If the user is not authenticated, it will call the _authenticate method before executing the function.
        """

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                if not self.authenticated:
                    await self.login()
            except SpaceTrackAuthenticationError:
                await self.logout()
                raise  
            return await func(self, *args, **kwargs)

        return wrapper

    @staticmethod
    def handle_logout(func: Callable) -> Callable:
        """
        Decorator to ensure the user is logged out after making an API call.
        Executes the decorated function, then calls self._deauthenticate().
        """

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            result = await func(self, *args, **kwargs)
            if self.authenticated:
                await self.close()

            return result

        return wrapper

    @staticmethod
    def handle_login_and_logout(func: Callable) -> Callable:
        """
        Decorator to ensure the user is logged in before making an API call
        and logged out after the call.
        """

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not self.authenticated:
                await self.login()
            result = await func(self, *args, **kwargs)
            if self.authenticated:
                await self.close()

            return result

        return wrapper
    