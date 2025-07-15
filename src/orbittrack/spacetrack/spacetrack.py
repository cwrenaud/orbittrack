"""
SpaceTrack API Synchronous Client
This module provides the `SpaceTrack` class, a synchronous client for interacting with
the SpaceTrack API.
It supports authentication, rate limiting, and convenient methods for retrieving general
perturbations (GP) data
and historical records for satellites using their NORAD catalog IDs.
Features:
- Automatic and manual authentication workflows with thread safety.
- Configurable rate limiting and storage backends for distributed or local enforcement.
- Methods for retrieving current and historical GP data, with support for date ranges.
- Robust error handling for authentication, network, and API errors.
- Context manager support for session management.
- Extensible with custom HTTP clients and rate limiting strategies.
Dependencies:
- httpx: For HTTP requests.
- limits: For rate limiting and storage backends.
- orbittrack.spacetrack.exceptions: Custom exception classes for error handling.
- orbittrack.spacetrack.models: Data models for API responses.
- orbittrack.spacetrack.spacetrackutils: Utility functions and decorators for
authentication and rate limiting.
Usage:
    with SpaceTrack(username, password) as st:
        gp_data = st.gp(norad_id)
        history = st.gp_history(norad_id, start_date, end_date)

"""

import threading
from typing import Any, Mapping, Optional

import httpx
from limits import parse
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
    SpaceTrackAuthenticationError,
    SpaceTrackRaiseStatusError,
    SpaceTrackRateLimitExceededError,
    SpaceTrackRequestError,
    SpaceTrackTimeoutError,
)
from orbittrack.spacetrack.models import SpaceTrackGPResponse
from orbittrack.spacetrack.spacetrackutils import SpaceTrackUtils


class SpaceTrack:
    """
    Synchronous client for interacting with the SpaceTrack API.

    Provides authentication, rate limiting, and convenient methods for retrieving
    general perturbations (GP) data and history.
    Supports both automatic and manual authentication workflows, and exposes
    configuration for rate limiting and storage.
    """

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = "https://www.space-track.org",
        http_client: Optional[httpx.Client] = None,
    ):
        """
        Initialize a SpaceTrack API client instance.

        Args:
            base_url (str): The base URL for the SpaceTrack API.
            username (str): The username for authentication.
            password (str): The password for authentication.
            http_client (Optional[httpx.Client]): An optional custom httpx.Client
            instance.
        """
        self.base_url: str = base_url
        self.username: str = username
        self.password: str = password
        self._authenticated: bool = False
        self.http_client: httpx.Client = http_client or httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
        self._auth_lock: threading.Lock = threading.Lock()

    # ===========================================
    # Properties
    # ===========================================
    @property
    def authenticated(self) -> bool:
        """
        Returns True if the user is currently authenticated with the SpaceTrack API,
        False otherwise.
        """
        return self._authenticated

    # ============================================
    # Authentication Methods - handled internally
    # ===========================================

    def _authenticate(self) -> None:
        """
        Authenticate the user with the SpaceTrack API using the provided credentials.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails due to invalid
            credentials or server error.
        """
        data = {
            "identity": self.username,
            "password": self.password,
        }

        response = self.http_client.post("/ajaxauth/login", data=data)
        response.raise_for_status()
        res = response.json()
        if isinstance(res, Mapping):
            if res.get("Login", None) == "Failed":
                raise SpaceTrackAuthenticationError(
                    """Authentication failed. Please check your SpaceTrack API
                    credentials."""
                )
        self._authenticated = True

    def _deauthenticate(self) -> None:
        """
        Deauthenticate the user by logging out of the SpaceTrack API and clearing the
        session.
        """
        if self._authenticated:
            self.http_client.get("/ajaxauth/logout")
            self._authenticated = False

    # ===========================================
    # Public API Methods - handles authentication automatically
    # ===========================================

    def login(self) -> None:
        """
        Authenticate the user if not already authenticated.

        Thread-safe. Calls the internal _authenticate method.
        """
        with self._auth_lock:
            if not self._authenticated:
                self._authenticate()

    def logout(self) -> None:
        """
        Deauthenticate the user by calling _deauthenticate.

        Thread-safe. Logs out if currently authenticated.
        """
        with self._auth_lock:
            if self._authenticated:
                self._deauthenticate()

    def close(self) -> None:
        """
        Close the HTTP client and log out if authenticated.

        Ensures resources are properly released and session is closed.
        """
        with self._auth_lock:
            if self._authenticated:
                self.logout()
            self.http_client.close()

    # ===========================================
    # Context Manager Methods
    # ===========================================

    def __aenter__(self) -> "SpaceTrack":
        """
        Enter the context manager, logging in and returning the SpaceTrack instance.
        """
        self.login()
        return self

    def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[Any],
    ) -> None:
        """
        Exit the context manager, logging out and closing the HTTP client.
        Ensures resources are properly released.
        """
        self.close()

    # ===========================================
    # Rate Limiting Methods
    # ===========================================
    def set_minute_rate_limit(self, limit: str) -> None:
        """
        Set the per-minute rate limit for SpaceTrack API requests.

        Args:
            limit (str): The desired rate limit as a string (e.g., "30/minute").

        Raises:
            SpaceTrackRateLimitExceededError: If the provided rate limit exceeds the
            default allowed limit.
        """
        provided_limit = parse(limit)
        try:
            SpaceTrackUtils.set_minute_rate_limit(provided_limit)
        except SpaceTrackRateLimitExceededError as e:
            raise SpaceTrackRateLimitExceededError(
                "This rate limit exceeds the default allowed limit."
            ) from e

    def set_hourly_rate_limit(self, limit: str) -> None:
        """
        Set the hourly rate limit for SpaceTrack API requests.

        Args:
            limit (str): The desired hourly rate limit as a string (e.g., "1000/hour").

        Raises:
            SpaceTrackRateLimitExceededError: If the provided limit exceeds the allowed
            maximum.
        """
        provided_limit = parse(limit)
        try:
            SpaceTrackUtils.set_hourly_rate_limit(provided_limit)
        except SpaceTrackRateLimitExceededError as e:
            raise SpaceTrackRateLimitExceededError(
                "This rate limit exceeds the default allowed limit."
            ) from e

    def set_ratelimit_storage(
        self,
        storage: MemoryStorage
        | MemcachedStorage
        | MongoDBStorage
        | RedisClusterStorage
        | RedisStorage
        | RedisSentinelStorage,
    ) -> None:
        """
        Configure the backend storage used for rate limiting in the SpaceTrack client.

        This method sets the storage mechanism for persisting rate limit counters and
        metadata. Supported backends include in-memory, Memcached, MongoDB, and various
        Redis storage types. The chosen storage affects how rate limits are enforced
        across processes or distributed systems.

        Args:
            storage: An instance of a supported storage backend from the
            `limits.storage` module, such as MemoryStorage, MemcachedStorage,
            MongoDBStorage, RedisClusterStorage, RedisStorage, or RedisSentinelStorage.

        Raises:
            SpaceTrackRateLimitExceededError: If the storage could not be set or is not
            supported.
        """
        try:
            SpaceTrackUtils.set_ratelimit_storage(storage)
        except Exception as e:
            raise SpaceTrackRateLimitExceededError(
                "Failed to set rate limit storage."
            ) from e

    def set_ratelimiter(
        self,
        ratelimiter: FixedWindowRateLimiter
        | MovingWindowRateLimiter
        | SlidingWindowCounterRateLimiter,
    ) -> None:
        """
        Set the rate limiter implementation for the SpaceTrack API.

        Args:
            ratelimiter: An instance of a supported rate limiter from the
            `limits.strategies` module.

        Raises:
            SpaceTrackRateLimitExceededError: If the rate limiter could not be set.
        """
        try:
            SpaceTrackUtils.set_ratelimiter(ratelimiter)
        except Exception as e:
            raise SpaceTrackRateLimitExceededError("Failed to set rate limiter.") from e

    # ===========================================
    # Private API Methods
    # ===========================================
    def _gp(self, filter_by: str, value: str) -> httpx.Response:
        """
        Internal method to retrieve general perturbations (GP) data for a satellite
        from the SpaceTrack API.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            httpx.Response: The HTTP response object from the API.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        try:
            response = self.http_client.get(
                f"/basicspacedata/query/class/gp/{filter_by}/{value}/orderby/CREATION_DATE%20asc/emptyresult/show"
            )
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise SpaceTrackTimeoutError(
                f"""The request to fetch GP data for {filter_by} {value} timed out.
                Please check your network connection or try again later."""
            ) from e
        except httpx.RequestError as e:
            raise SpaceTrackRequestError(
                f"""A network error occurred while fetching GP data for
                {filter_by} {value}: {e!r}"""
            ) from e
        except httpx.HTTPStatusError as e:
            raise SpaceTrackRaiseStatusError(
                f"""SpaceTrack API returned HTTP {e.response.status_code} while fetching
                GP data for {filter_by} {value}: {e.response.text}"""
            ) from e

    def _all_gp_history(self, filter_by: str, value: str) -> httpx.Response:
        """
        Internal method to retrieve all historical general perturbations (GP) data for a
        satellite from the SpaceTrack API.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            httpx.Response: The HTTP response object from the API.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        try:
            response = self.http_client.get(
                f"basicspacedata/query/class/gp_history/{filter_by}/{value}/orderby/NORAD_CAT_ID%20asc/emptyresult/show"
            )
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise SpaceTrackTimeoutError(
                f"""The request to fetch all GP history for {filter_by} {value}
                timed out. Please check your network connection or try again later."""
            ) from e
        except httpx.RequestError as e:
            raise SpaceTrackRequestError(
                f"""A network error occurred while fetching all GP history for
                {filter_by} {value}: {e!r}"""
            ) from e
        except httpx.HTTPStatusError as e:
            raise SpaceTrackRaiseStatusError(
                f"""SpaceTrack API returned HTTP {e.response.status_code} while fetching
                all GP history for {filter_by} {value}: {e.response.text}"""
            ) from e

    def _gp_history(
        self, filter_by: str, value: str, start_date: str, end_date: str
    ) -> httpx.Response:
        """
        Internal method to retrieve general perturbations (GP) history for a satellite
        within a date range from the SpaceTrack API.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.
            start_date (str): The start date for the history range (format: YYYY-MM-DD).
            end_date (str): The end date for the history range (format: YYYY-MM-DD).

        Returns:
            httpx.Response: The HTTP response object from the API.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        try:
            response = self.http_client.get(
                f"basicspacedata/query/class/gp_history/{filter_by}/{value}/EPOCH/{start_date}--{end_date}/orderby/EPOCH%20asc/emptyresult/show"
            )
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise SpaceTrackTimeoutError(
                f"""The request to fetch GP history for {filter_by} {value} from
                {start_date} to {end_date} timed out. Please check your network
                connection or try again later."""
            ) from e
        except httpx.RequestError as e:
            raise SpaceTrackRequestError(
                f"""A network error occurred while fetching GP history for {filter_by}
                {value} from {start_date} to {end_date}: {e!r}"""
            ) from e
        except httpx.HTTPStatusError as e:
            raise SpaceTrackRaiseStatusError(
                f"""SpaceTrack API returned HTTP {e.response.status_code} while fetching
                GP history for {filter_by} {value} from {start_date} to {end_date}:
                {e.response.text}"""
            ) from e

    def _custom_query(self, query: str) -> httpx.Response:
        """
        Internal method to execute a custom query against the SpaceTrack API.

        Args:
            query (str): The custom query string to execute.

        Returns:
            httpx.Response: The HTTP response object from the API.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        try:
            response = self.http_client.get(query)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise SpaceTrackTimeoutError(
                f"""The request for custom query '{query}' timed out. Please check your
                network connection or try again later."""
            ) from e
        except httpx.RequestError as e:
            raise SpaceTrackRequestError(
                f"""A network error occurred while executing custom query '{query}':
                {e!r}"""
            ) from e
        except httpx.HTTPStatusError as e:
            raise SpaceTrackRaiseStatusError(
                f"""SpaceTrack API returned HTTP {e.response.status_code} for custom
                query '{query}': {e.response.text}"""
            ) from e

    # ===========================================
    # Public API Methods - handles authentication automatically
    # ===========================================
    @SpaceTrackUtils.handle_login_and_logout
    @SpaceTrackUtils.ratelimit
    def gp(self, filter_by: str, value: str) -> SpaceTrackGPResponse:
        """
        Retrieve general perturbations (GP) data for a satellite from the SpaceTrack
        API.

        This method authenticates the user if necessary, sends a GET request to the
        SpaceTrack API
        for the specified NORAD catalog ID, and returns the response data wrapped in a
        SpaceTrackGPResponse object.
        The user is logged out and the HTTP client is closed after the request.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            SpaceTrackGPResponse: The parsed response data from the API.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        response = self._gp(filter_by, value)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @SpaceTrackUtils.handle_login_and_logout
    @SpaceTrackUtils.ratelimit
    def all_gp_history(self, filter_by: str, value: str) -> SpaceTrackGPResponse:
        """
        Retrieve all historical general perturbations (GP) data for a satellite from the
        SpaceTrack API.

        This method authenticates the user if necessary, sends a GET request to the
        SpaceTrack API
        for the specified NORAD catalog ID, and returns the response data wrapped in a
        SpaceTrackGPResponse object.
        The user is logged out and the HTTP client is closed after the request.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            SpaceTrackGPResponse: The parsed response data from the API.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        response = self._all_gp_history(filter_by, value)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @SpaceTrackUtils.handle_login_and_logout
    @SpaceTrackUtils.ratelimit
    def gp_history(
        self, filter_by: str, value: str, start_date: str, end_date: str
    ) -> SpaceTrackGPResponse:
        """
        Retrieve general perturbations (GP) history for a satellite within a date range
        from the SpaceTrack API.

        This method authenticates the user if necessary, sends a GET request to the
        SpaceTrack API
        for the specified NORAD catalog ID and date range, and returns the response
        data wrapped in a SpaceTrackGPResponse object.
        The user is logged out and the HTTP client is closed after the request.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.
            start_date (str): The start date for the history range (format: YYYY-MM-DD).
            end_date (str): The end date for the history range (format: YYYY-MM-DD).

        Returns:
            SpaceTrackGPResponse: The parsed response data from the API.

        Raises:
            SpaceTrackAuthenticationError: If authentication fails.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        response = self._gp_history(filter_by, value, start_date, end_date)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    def custom_query(self, query: str) -> httpx.Response:
        """
        Execute a custom query against the SpaceTrack API asynchronously.

        Args:
            query (str): The custom query string to execute.

        Returns:
            httpx.Response: The HTTP response object from the API.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        response = self._custom_query(query)
        return response

    # ===========================================
    # Public API Methods - handles authentication manually
    # ===========================================
    @SpaceTrackUtils.ratelimit
    def gp_session(self, filter_by: str, value: str) -> SpaceTrackGPResponse:
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
            SpaceTrackGPResponse: The parsed response data from the API.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        if not self._authenticated:
            raise SpaceTrackAuthenticationError(
                """User is not authenticated. Please call login() before using this
                method."""
            )
        response = self._gp(filter_by, value)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @SpaceTrackUtils.ratelimit
    def all_gp_history_session(
        self, filter_by: str, value: str
    ) -> SpaceTrackGPResponse:
        """
        Retrieve all historical general perturbations (GP) data for a satellite from the
        SpaceTrack API within an authenticated session.

        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        It requires the user to be authenticated before calling, and does not perform
        login or logout automatically.

        Args:
            norad_id (str): The NORAD catalog ID of the satellite.

        Returns:
            SpaceTrackGPResponse: The parsed response data from the API.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        if not self._authenticated:
            raise SpaceTrackAuthenticationError(
                """User is not authenticated. Please call login() before using this
                method."""
            )
        response = self._all_gp_history(filter_by, value)
        response.raise_for_status()
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    @SpaceTrackUtils.ratelimit
    def gp_history_session(
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
            SpaceTrackGPResponse: The parsed response data from the API.

        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        if not self._authenticated:
            raise SpaceTrackAuthenticationError(
                """User is not authenticated. Please call login() before using this
                method."""
            )
        response = self._gp_history(filter_by, value, start_date, end_date)
        return SpaceTrackGPResponse(
            status_code=response.status_code,
            **response.json(),
        )

    def custom_query_session(self, query: str) -> httpx.Response:
        """
        Execute a custom query against the SpaceTrack API asynchronously within an
        authenticated session.
        This method is intended to be used when the user manages authentication manually
        (e.g., via a context manager or explicit login/logout).
        Args:
            query (str): The custom query string to execute.
        Returns:
            httpx.Response: The HTTP response object from the API.
        Raises:
            SpaceTrackAuthenticationError: If the user is not authenticated.
            httpx.HTTPStatusError: If the HTTP request fails.
        """
        if not self._authenticated:
            raise SpaceTrackAuthenticationError(
                """User is not authenticated. Please call login() before using this
                method."""
            )
        response = self._custom_query(query)
        return response
