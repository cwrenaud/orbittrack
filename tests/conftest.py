"""
Configuration file for pytest.
This file contains fixtures and setup code for tests.
"""
from typing import AsyncGenerator, Generator

import httpx
import pytest
import pytest_asyncio
from limits.aio.storage import MemoryStorage as AsyncMemoryStorage
from limits.aio.strategies import (
    MovingWindowRateLimiter as AsyncMovingWindowRateLimiter,
)
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from orbittrack.spacetrack.aio.spacetrackaio import AsyncSpaceTrack
from orbittrack.spacetrack.aio.spacetrackutilsaio import AsyncSpaceTrackUtils
from orbittrack.spacetrack.spacetrack import SpaceTrack
from orbittrack.spacetrack.spacetrackutils import SpaceTrackUtils


@pytest.fixture
def mock_http_client() -> Generator[httpx.Client, None, None]:
    """
    Creates a mock httpx Client for testing.
    """
    # Use httpx MockTransport or MockResponse for more advanced mocking
    client = httpx.Client(base_url="https://www.space-track.org")
    yield client
    client.close()


@pytest.fixture
def spacetrack_client(mock_http_client) -> Generator[SpaceTrack, None, None]:
    """
    Creates a SpaceTrack client with mock credentials for testing.
    """
    # Reset rate limit storage before each test
    SpaceTrackUtils._ratelimit_storage = MemoryStorage()
    SpaceTrackUtils._ratelimit_limiter = MovingWindowRateLimiter(
        SpaceTrackUtils._ratelimit_storage
    )
    
    client = SpaceTrack(
        username="test_user",
        password="test_pass",
        http_client=mock_http_client,
    )
    yield client
    client.close()


@pytest_asyncio.fixture
async def mock_async_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Creates a mock httpx AsyncClient for testing.
    """
    AsyncSpaceTrackUtils._ratelimit_storage = AsyncMemoryStorage()
    AsyncSpaceTrackUtils._ratelimit_limiter = AsyncMovingWindowRateLimiter(
        AsyncSpaceTrackUtils._ratelimit_storage
    )
    client = httpx.AsyncClient(base_url="https://www.space-track.org")
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def async_spacetrack_client(
    mock_async_http_client
) -> AsyncGenerator[AsyncSpaceTrack, None]:
    """
    Creates an AsyncSpaceTrack client with mock credentials for testing.
    """
    # Reset rate limit storage before each test
    AsyncSpaceTrackUtils._ratelimit_storage = AsyncMemoryStorage()
    AsyncSpaceTrackUtils._ratelimit_limiter = AsyncMovingWindowRateLimiter(
        AsyncSpaceTrackUtils._ratelimit_storage
    )
    
    client = AsyncSpaceTrack(
        username="test_user",
        password="test_pass",
        http_client=mock_async_http_client,
    )
    yield client
    await client.close()
