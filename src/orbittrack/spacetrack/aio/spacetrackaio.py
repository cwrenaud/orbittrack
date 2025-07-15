import asyncio
from typing import Any, Mapping, Optional

import httpx
from limits import parse
from limits.aio.storage import MemcachedStorage as AsyncMemcachedStorage
from limits.aio.storage import MemoryStorage as AsyncMemoryStorage
from limits.aio.storage import MongoDBStorage as AsyncMongoDBStorage
from limits.aio.storage import RedisClusterStorage as AsyncRedisClusterStorage
from limits.aio.storage import RedisSentinelStorage as AsyncRedisSentinelStorage
from limits.aio.storage import RedisStorage as AsyncRedisStorage
from limits.aio.strategies import FixedWindowRateLimiter as AsyncFixedWindowRateLimiter
from limits.aio.strategies import (
    MovingWindowRateLimiter as AsyncMovingWindowRateLimiter,
)
from limits.aio.strategies import (
    SlidingWindowCounterRateLimiter as AsyncSlidingWindowCounterRateLimiter,
)

from orbittrack.spacetrack.aio.spacetrackutilsaio import AsyncSpaceTrackUtils
from orbittrack.spacetrack.exceptions import (
    AsyncSpaceTrackAsyncTimeoutError,
    AsyncSpaceTrackHttpxTimeoutError,
    AsyncSpaceTrackRaiseStatusError,
    AsyncSpaceTrackRequestError,
    SpaceTrackAuthenticationError,
    SpaceTrackRateLimitExceededError,
)
from orbittrack.spacetrack.models import (
    SpaceTrackAnnouncementResponse,
    SpaceTrackGPResponse,
)


class AsyncSpaceTrack:
    """
    Asynchronous SpaceTrack API client for retrieving satellite data.
    """

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = "https://www.space-track.org",
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """
        Initialize a SpaceTrack API client instance.

        Args:
            base_url (str): The base URL for the SpaceTrack API.
            username (str): The username for authentication.
            password (str): The password for authentication.
            http_client (Optional[httpx.AsyncClient]):
                An optional custom AsyncClient instance.
        """
        self.base_url: str = base_url
        self.username: str = username
        self.password: str = password
        self._authenticated: bool = False
        self.http_client: httpx.AsyncClient = http_client or httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
        self._auth_lock: asyncio.Lock = asyncio.Lock()

    # ===========================================
    # Properties
    # ===========================================
    @property
    def authenticated(self) -> bool:
        """
        Check if the user is authenticated.

        Returns:
            bool: True if authenticated, False otherwise.
        """
        return self._authenticated

    # ===========================================
    # Authentication Methods - handled internally
    # ===========================================

    async def _authenticate(self) -> None:
        """
        Authenticate the user with the SpaceTrack API using the provided credentials.
        Raises SpaceTrackAuthenticationError if authentication fails.
        """
        data = {
            "identity": self.username,
            "password": self.password,
        }

        response = await self.http_client.post("/ajaxauth/login", data=data)
        response.raise_for_status()
        res = response.json()
        if isinstance(res, Mapping):
            if res.get("Login", None) == "Failed":
                raise SpaceTrackAuthenticationError(
                    """Authentication failed.
                    Please check your SpaceTrack API credentials."""
                )
        self._authenticated = True

    async def _deauthenticate(self) -> None:
        """
        Deauthenticate the user by logging out of the
        SpaceTrack API and clearing the session.
        """

        if self._authenticated:
            await self.http_client.get("/ajaxauth/logout")
            self._authenticated = False

    # ===========================================
    # Public API Methods - handles authentication automatically
    # ===========================================

    async def login(self) -> None:
        """
        Public method to authenticate the user if not already authenticated.
        Calls the internal _authenticate method.
        """
        async with self._auth_lock:
            if not self._authenticated:
                await self._authenticate()

    async def logout(self) -> None:
        """
        Public method to deauthenticate the user by calling _deauthenticate.
        """
        async with self._auth_lock:
            if self._authenticated:
                await self._deauthenticate()

    async def close(self) -> None:
        """
        Close the HTTP client and log out if authenticated.
        Ensures resources are properly released.
        """
        async with self._auth_lock:
            if self._authenticated:
                await self.logout()
            await self.http_client.aclose()

    # ===========================================
    # Context Manager Methods
    # ===========================================

    async def __aenter__(self) -> "AsyncSpaceTrack":
        """
        Context manager entry method to log in and return the SpaceTrack instance.
        """
        await self.login()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[Any],
    ) -> None:
        """
        Context manager exit method to log out and close the HTTP client.
        Ensures resources are properly released.
        """
        await self.close()

    # ===========================================
    # Rate Limiting Methods
    # ===========================================
    def set_minute_rate_limit(self, limit: str) -> None:
        """
        Set the per-minute rate limit for SpaceTrack API requests.

        Args:
            limit (str): The desired rate limit as a string (e.g., "30/minute").

        Raises:
            SpaceTrackRateLimitExceededError:
                If the provided rate limit exceeds the default allowed limit.

        This method parses the provided rate limit
        and applies it using AsyncSpaceTrackUtils.
        If the specified limit is too high,
        a SpaceTrackRateLimitExceededError is raised.
        """
        provided_limit = parse(limit)
        try:
            AsyncSpaceTrackUtils.set_minute_rate_limit(provided_limit)
        except SpaceTrackRateLimitExceededError as e:
            raise SpaceTrackRateLimitExceededError(
                "This rate limit exceeds the default allowed limit."
            ) from e

    def set_hourly_rate_limit(self, limit: str) -> None:
        """
        Set the hourly rate limit for SpaceTrack API requests.

        Parses the provided limit and attempts to set it using AsyncSpaceTrackUtils.
        If the provided limit exceeds the default allowed limit,
        raises a SpaceTrackRateLimitExceededError.

        Args:
            limit (str): The desired hourly rate limit as a string.

        Raises:
            SpaceTrackRateLimitExceededError:
                If the provided limit exceeds the allowed maximum.
        """
        provided_limit = parse(limit)
        try:
            AsyncSpaceTrackUtils.set_hourly_rate_limit(provided_limit)
        except SpaceTrackRateLimitExceededError as e:
            raise SpaceTrackRateLimitExceededError(
                "This rate limit exceeds the default allowed limit."
            ) from e

    def set_ratelimit_storage(
        self,
        storage: AsyncMemoryStorage
        | AsyncMemcachedStorage
        | AsyncMongoDBStorage
        | AsyncRedisClusterStorage
        | AsyncRedisStorage
        | AsyncRedisSentinelStorage,
    ) -> None:
        """
        Sets the storage backend for rate limiting.

        This method configures the storage mechanism used to persist
        rate limit data for the SpaceTrack client.
        Supported storage backends include various asynchronous
        memory and database storage types.

        Args:
            storage: An instance of one of the supported asynchronous storage backends:
                - AsyncMemoryStorage
                - AsyncMemcachedStorage
                - AsyncMongoDBStorage
                - AsyncRedisClusterStorage
                - AsyncRedisStorage
                - AsyncRedisSentinelStorage

        Raises:
            SpaceTrackRateLimitExceededError: If setting the rate limit storage fails.
        """
        try:
            AsyncSpaceTrackUtils.set_ratelimit_storage(storage)
        except Exception as e:
            raise SpaceTrackRateLimitExceededError(
                "Failed to set rate limit storage."
            ) from e

    def set_ratelimiter(
        self,
        ratelimiter: AsyncFixedWindowRateLimiter
        | AsyncMovingWindowRateLimiter
        | AsyncSlidingWindowCounterRateLimiter,
    ) -> None:
        """
        Set the rate limiter implementation for the SpaceTrack API client.

        This method allows you to provide a custom rate limiter strategy,
        which controls how API request rates are enforced.
        Supported rate limiters include AsyncFixedWindowRateLimiter,
        AsyncMovingWindowRateLimiter, and AsyncSlidingWindowCounterRateLimiter.

        Args:
            ratelimiter: An instance of a supported asynchronous
            rate limiter from the `limits.aio.strategies` module.

        Raises:
            SpaceTrackRateLimitExceededError: If the rate
            limiter could not be set or is not supported.
        """
        try:
            AsyncSpaceTrackUtils.set_ratelimiter(ratelimiter)
        except Exception as e:
            raise SpaceTrackRateLimitExceededError("Failed to set rate limiter.") from e

    # ===========================================
    # Private API Methods
    # ===========================================

    async def _gp(self, filter_by: str, value: str) -> httpx.Response:
        """
        Retrieve general perturbations (GP) data for a satellite from the SpaceTrack
        API.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling,
        and does not perform login or logout automatically.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            Response: A Response object containing the HTTP
            status code and the API response data.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        try:
            response = await self.http_client.get(
                f"/basicspacedata/query/class/gp/{filter_by}/{value}/orderby/CREATION_DATE%20asc/emptyresult/show"
            )
            response.raise_for_status()
            return response
        except asyncio.TimeoutError as e:
            raise AsyncSpaceTrackAsyncTimeoutError(
                f"""The request to SpaceTrack timed out (asyncio.TimeoutError)
                while retrieving GP data for {filter_by} {value}: {str(e)}"""
            ) from e
        except httpx.TimeoutException as e:
            raise AsyncSpaceTrackHttpxTimeoutError(
                f"""The request to SpaceTrack timed out (httpx.TimeoutException)
                while retrieving GP data for {filter_by} {value}: {str(e)}"""
            ) from e
        except httpx.HTTPStatusError as e:
            raise AsyncSpaceTrackRaiseStatusError(
                f"""SpaceTrack API returned an unsuccessful HTTP status
                ({e.response.status_code})while retrieving GP data
                for {filter_by} {value}: {e.response.text}"""
            ) from e
        except httpx.RequestError as e:
            raise AsyncSpaceTrackRequestError(
                f"""A network error occurred while requesting
                GP data for {filter_by} {value}: {str(e)}"""
            ) from e

    async def _all_gp_history(self, filter_by: str, value: str) -> httpx.Response:
        """
        Retrieve historical general perturbations (GP) data for
        a satellite from the SpaceTrack API.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling,
        and does not perform login or logout automatically.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            Response: A Response object containing the HTTP status code
            and the API response data.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        try:
            response = await self.http_client.get(
                f"basicspacedata/query/class/gp_history/{filter_by}/{value}/orderby/NORAD_CAT_ID%20asc/emptyresult/show"
            )
            response.raise_for_status()
            return response
        except asyncio.TimeoutError as e:
            raise AsyncSpaceTrackAsyncTimeoutError(
                f"""The request to SpaceTrack timed out (asyncio.TimeoutError)
                while retrieving all GP history for {filter_by} {value}: {str(e)}"""
            ) from e
        except httpx.TimeoutException as e:
            raise AsyncSpaceTrackHttpxTimeoutError(
                f"""The request to SpaceTrack timed out (httpx.TimeoutException)
                while retrieving all GP history for {filter_by} {value}: {str(e)}"""
            ) from e
        except httpx.HTTPStatusError as e:
            raise AsyncSpaceTrackRaiseStatusError(
                f"""SpaceTrack API returned an unsuccessful HTTP status
                ({e.response.status_code})while retrieving all GP history
                for {filter_by} {value}: {e.response.text}"""
            ) from e
        except httpx.RequestError as e:
            raise AsyncSpaceTrackRequestError(
                f"""A network error occurred while requesting all GP history
                for {filter_by} {value}: {str(e)}"""
            ) from e

    async def _gp_history(
        self, filter_by: str, value: str, start_date: str, end_date: str
    ) -> httpx.Response:
        """
        Retrieve general perturbations (GP) history for a satellite within
        a date range from the SpaceTrack API.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling, and does not
        perform login or logout automatically.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.
            start_date (str): The start date for the history range (format: YYYY-MM-DD).
            end_date (str): The end date for the history range (format: YYYY-MM-DD).

        Returns:
            Response: A Response object containing the HTTP
            status code and the API response data.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        try:
            response = await self.http_client.get(
                f"basicspacedata/query/class/gp_history/{filter_by}/{value}/EPOCH/{start_date}--{end_date}/orderby/EPOCH%20asc/emptyresult/show"
            )
            response.raise_for_status()
            return response
        except asyncio.TimeoutError as e:
            raise AsyncSpaceTrackAsyncTimeoutError(
                f"""The request to SpaceTrack timed out (asyncio.TimeoutError) while
                retrieving GP history for {filter_by} {value} between {start_date} and
                {end_date}: {str(e)}"""
            ) from e
        except httpx.TimeoutException as e:
            raise AsyncSpaceTrackHttpxTimeoutError(
                f"""The request to SpaceTrack timed out (httpx.TimeoutException) while
                retrieving GP history for {filter_by} {value} between {start_date} and
                {end_date}: {str(e)}"""
            ) from e
        except httpx.HTTPStatusError as e:
            raise AsyncSpaceTrackRaiseStatusError(
                f"""SpaceTrack API returned an unsuccessful HTTP status
                ({e.response.status_code}) while retrieving GP history for
                {filter_by} {value} between {start_date} and {end_date}:
                {e.response.text}
                """
            ) from e
        except httpx.RequestError as e:
            raise AsyncSpaceTrackRequestError(
                f"""A network error occurred while requesting GP history for {filter_by}
                {value} between {start_date} and {end_date}: {str(e)}"""
            ) from e

    async def _custom_query(self, query: str) -> httpx.Response:
        """
        Perform a custom query against the SpaceTrack API.

        Args:
            query (str): The custom query string to execute.

        Returns:
            Response: A Response object containing the HTTP status code and the
            API response data.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        try:
            response = await self.http_client.get(f"{query}")
            response.raise_for_status()
            return response
        except asyncio.TimeoutError as e:
            raise AsyncSpaceTrackAsyncTimeoutError(
                f"The request to SpaceTrack timed out (asyncio.TimeoutError) "
                f"while executing custom query '{query}': {str(e)}"
            ) from e
        except httpx.TimeoutException as e:
            raise AsyncSpaceTrackHttpxTimeoutError(
                f"The request to SpaceTrack timed out (httpx.TimeoutException) "
                f"while executing custom query '{query}': {str(e)}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise AsyncSpaceTrackRaiseStatusError(
                f"SpaceTrack API returned an unsuccessful HTTP status "
                f"({e.response.status_code}) while executing custom query "
                f"'{query}': {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise AsyncSpaceTrackRequestError(
                f"A network error occurred while executing custom query "
                f"'{query}': {str(e)}"
            ) from e

    async def _announcement(self) -> httpx.Response:
        """
        Retrieve the latest announcements from the SpaceTrack API.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling,
        and does not perform login or logout automatically.

        Returns:
            Response: A Response object containing the HTTP status code and the API
            response data.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        try:
            response = await self.http_client.get("/announcements")
            response.raise_for_status()
            return response
        except asyncio.TimeoutError as e:
            raise AsyncSpaceTrackAsyncTimeoutError(
                f"The request to SpaceTrack timed out (asyncio.TimeoutError) "
                f"while retrieving announcements: {str(e)}"
            ) from e
        except httpx.TimeoutException as e:
            raise AsyncSpaceTrackHttpxTimeoutError(
                f"The request to SpaceTrack timed out (httpx.TimeoutException) "
                f"while retrieving announcements: {str(e)}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise AsyncSpaceTrackRaiseStatusError(
                f"SpaceTrack API returned an unsuccessful HTTP status "
                f"({e.response.status_code}) while retrieving announcements: "
                f"{e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise AsyncSpaceTrackRequestError(
                f"A network error occurred while retrieving announcements: {str(e)}"
            ) from e

    # ===========================================
    # Public API Methods - handles authentication automatically
    # ===========================================
    @AsyncSpaceTrackUtils.handle_login_and_logout
    @AsyncSpaceTrackUtils.ratelimit
    async def gp(self, filter_by: str, value: str) -> SpaceTrackGPResponse:
        """
        Retrieve general perturbations (GP) data for a satellite
        from the SpaceTrack API.

        This method authenticates the user if necessary, sends a GET request to the
        SpaceTrack API
        for the specified NORAD catalog ID, and returns the response data wrapped in a
        Response object.
        The user is logged out and the HTTP client is closed after the request.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            Response: A Response object containing the HTTP status code and the API
            response data.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails.
            httpx.HTTPStatusError: If the HTTP request fails.
        """

        response = await self._gp(filter_by, value)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @AsyncSpaceTrackUtils.handle_login_and_logout
    @AsyncSpaceTrackUtils.ratelimit
    async def all_gp_history(self, filter_by: str, value: str) -> SpaceTrackGPResponse:
        """
        Retrieve historical general perturbations (GP) data for a satellite from the
        SpaceTrack API.

        This method authenticates the user if necessary, sends a GET request to the
        SpaceTrack API
        for the specified NORAD catalog ID, and returns the response data wrapped in a
        Response object.
        The user is logged out and the HTTP client is closed after the request.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            Response: A Response object containing the HTTP status code and the API
            response data.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails.
            httpx.HTTPStatusError: If the HTTP request fails.
        """

        response = await self._all_gp_history(filter_by, value)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @AsyncSpaceTrackUtils.handle_login_and_logout
    @AsyncSpaceTrackUtils.ratelimit
    async def gp_history(
        self, filter_by: str, value: str, start_date: str, end_date: str
    ) -> SpaceTrackGPResponse:
        """
        Retrieve general perturbations (GP) history for a satellite within a date range
        from the SpaceTrack API.

        This method authenticates the user if necessary, sends a GET request to the
        SpaceTrack API
        for the specified NORAD catalog ID and date range, and returns the response data
        wrapped in a Response object.
        The user is logged out and the HTTP client is closed after the request.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.
            start_date (str): The start date for the history range (format: YYYY-MM-DD).
            end_date (str): The end date for the history range (format: YYYY-MM-DD).

        Returns:
            Response: A Response object containing the HTTP status code and the API
            response data.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        response = await self._gp_history(filter_by, value, start_date, end_date)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @AsyncSpaceTrackUtils.handle_login_and_logout
    @AsyncSpaceTrackUtils.ratelimit
    async def custom_query(self, query: str) -> httpx.Response:
        """
        Perform a custom query against the SpaceTrack API.

        This method authenticates the user if necessary, sends a GET request to the
        SpaceTrack API with the provided query, and returns the response data.

        Args:
            query (str): The custom query string to execute.

        Returns:
            Response: A Response object containing the HTTP status code and the
            API response data.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        response = await self._custom_query(query)
        return response

    @AsyncSpaceTrackUtils.handle_login_and_logout
    @AsyncSpaceTrackUtils.ratelimit
    async def announcement(self) -> SpaceTrackAnnouncementResponse:
        """
        Retrieve announcements from the SpaceTrack API.

        This method authenticates the user if necessary, sends a GET request to the
        SpaceTrack API for announcements, and returns the response data.

        The user is logged out and the HTTP client is closed after the request.

        Returns:
            Response: A Response object containing the HTTP status code and the
            API response data.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        response = await self._announcement()
        return SpaceTrackAnnouncementResponse(
            status_code=response.status_code,
            **response.json(),
        )

    # ===========================================
    # Public API Methods - handles authentication manually
    # ===========================================

    @AsyncSpaceTrackUtils.ratelimit
    async def gp_session(self, filter_by: str, value: str) -> SpaceTrackGPResponse:
        """
        Retrieve general perturbations (GP) data for a satellite from the SpaceTrack API
        within an authenticated session.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling, and does not perform
        login or logout automatically.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            Response: A Response object containing the HTTP status code and the API
            response data.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        if not self._authenticated:
            raise SpaceTrackAuthenticationError(
                """User is not authenticated. Please call login() before using this
                method."""
            )
        response = await self._gp(filter_by, value)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @AsyncSpaceTrackUtils.ratelimit
    async def all_gp_history_session(
        self, filter_by: str, value: str
    ) -> SpaceTrackGPResponse:
        """
        Retrieve historical general perturbations (GP) data for a satellite from the
        SpaceTrack API within an authenticated session.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling, and does not perform
        login or logout automatically.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            Response: A Response object containing the HTTP status code and the API
            response data.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        if not self._authenticated:
            raise SpaceTrackAuthenticationError(
                """User is not authenticated. Please call login() before using this
                method."""
            )
        response = await self._all_gp_history(filter_by, value)
        response.raise_for_status()
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @AsyncSpaceTrackUtils.ratelimit
    async def gp_history_session(
        self, filter_by: str, value: str, start_date: str, end_date: str
    ) -> SpaceTrackGPResponse:
        """
        Retrieve general perturbations (GP) history for a satellite within a date range
        from the SpaceTrack API within an authenticated session.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling, and does not perform
        login or logout automatically.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.
            start_date (str): The start date for the history range (format: YYYY-MM-DD).
            end_date (str): The end date for the history range (format: YYYY-MM-DD).

        Returns:
            Response: A Response object containing the HTTP status code and the API
            response data.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        if not self._authenticated:
            raise SpaceTrackAuthenticationError(
                """User is not authenticated. Please call login() before using this
                method."""
            )
        response = await self._gp_history(filter_by, value, start_date, end_date)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @AsyncSpaceTrackUtils.ratelimit
    async def custom_query_session(self, query: str) -> httpx.Response:
        """
        Perform a custom query against the SpaceTrack API within an authenticated
        session.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling, and does not perform
        login or logout automatically.

        Args:
            query (str): The custom query string to execute.

        Returns:
            Response: A Response object containing the HTTP status code and the API
            response data.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        if not self._authenticated:
            raise SpaceTrackAuthenticationError(
                """User is not authenticated. Please call login() before using this
                method."""
            )
        response = await self._custom_query(query)
        return response

    @AsyncSpaceTrackUtils.ratelimit
    async def announcement_session(self) -> SpaceTrackAnnouncementResponse:
        """
        Retrieve announcements from the SpaceTrack API within an authenticated session.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling, and does not perform
        login or logout automatically.

        Returns:
            Response: A Response object containing the HTTP status code and the API
            response data.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        if not self._authenticated:
            raise SpaceTrackAuthenticationError(
                """User is not authenticated. Please call login() before using this
                method."""
            )
        response = await self._announcement()
        return SpaceTrackAnnouncementResponse(
            status_code=response.status_code,
            **response.json(),
        )
