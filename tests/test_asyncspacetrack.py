"""
Tests for the AsyncSpaceTrack client.
"""
from unittest.mock import patch, AsyncMock, MagicMock
from collections.abc import Mapping

import httpx
import pytest

from orbittrack.spacetrack.aio.spacetrackaio import AsyncSpaceTrack
from orbittrack.spacetrack.exceptions import (
    SpaceTrackAuthenticationError,
    SpaceTrackRateLimitExceededError,
)
from orbittrack.spacetrack.models import SpaceTrackGPResponse


class TestAsyncSpaceTrack:
    """
    Tests for the asynchronous SpaceTrack client.
    """

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test that the AsyncSpaceTrack client initializes correctly."""
        client = AsyncSpaceTrack(username="test_user", password="test_pass")
        
        assert client.base_url == "https://www.space-track.org"
        assert client.username == "test_user"
        assert client.password == "test_pass"
        assert not client.authenticated
        assert isinstance(client.http_client, httpx.AsyncClient)
        
        # Clean up resources
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_login_success(self, mock_post, async_spacetrack_client):
        """Test successful login."""
        # Mock the response
        mock_response = MagicMock()
        # mock_response.status_code = 200
        mock_response.json.return_value = None
        mock_post.return_value = mock_response
        
        # Call login
        await async_spacetrack_client.login()
        
        # Assert that post was called with the correct arguments
        mock_post.assert_awaited_once_with("/ajaxauth/login", data={
            "identity": "test_user",
            "password": "test_pass"
        })
        
        # Assert that the client is now authenticated
        assert async_spacetrack_client.authenticated

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_login_failure(self, mock_post, async_spacetrack_client):
        """Test login failure."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Login": "Failed"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        # Call login and assert it raises the correct exception
        with pytest.raises(SpaceTrackAuthenticationError):
            await async_spacetrack_client.login()
        
        # Assert that the client is not authenticated
        assert not async_spacetrack_client.authenticated

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_logout(self, mock_get, async_spacetrack_client):
        """Test logout."""
        # Set the client as authenticated
        async_spacetrack_client._authenticated = True
        
        # Call logout
        await async_spacetrack_client.logout()
        
        # Assert that get was called with the correct arguments
        mock_get.assert_awaited_once_with("/ajaxauth/logout")
        
        # Assert that the client is no longer authenticated
        assert not async_spacetrack_client.authenticated

    @pytest.mark.asyncio
    @patch("orbittrack.spacetrack.aio.spacetrackutilsaio.AsyncSpaceTrackUtils.set_minute_rate_limit")
    async def test_set_minute_rate_limit(self, mock_set_limit, async_spacetrack_client):
        """Test setting the minute rate limit."""
        # Call the method
        async_spacetrack_client.set_minute_rate_limit("20/minute")
        
        # Assert that the method was called with the correct arguments
        mock_set_limit.assert_called_once()
        assert mock_set_limit.call_args[0][0].amount == 20
        
    @pytest.mark.asyncio
    @patch("orbittrack.spacetrack.aio.spacetrackutilsaio.AsyncSpaceTrackUtils.set_minute_rate_limit")
    async def test_set_minute_rate_limit_exceeded(self, mock_set_limit, async_spacetrack_client):
        """Test that setting a minute rate limit that exceeds the default raises an exception."""
        # Set the mock to raise an exception
        mock_set_limit.side_effect = SpaceTrackRateLimitExceededError("Rate limit exceeded")
        
        # Call the method and assert it raises the correct exception
        with pytest.raises(SpaceTrackRateLimitExceededError):
            async_spacetrack_client.set_minute_rate_limit("100/minute")

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_gp(self, mock_get, async_spacetrack_client):
        """Test retrieving GP data."""
        # Sample response data
        sample_data = {
            "NORAD_CAT_ID": 25544,
            "OBJECT_NAME": "ISS (ZARYA)",
            "EPOCH": "2023-06-01T12:00:00",
        }
        
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_data
        mock_get.return_value = mock_response
        
        # Mock authentication
        async_spacetrack_client._authenticated = True
        
        # Mock the rate limiter and handle_login_and_logout decorator
        with patch("orbittrack.spacetrack.aio.spacetrackutilsaio.AsyncSpaceTrackUtils.ratelimit", 
                  lambda func: func):
            with patch("orbittrack.spacetrack.aio.spacetrackutilsaio.AsyncSpaceTrackUtils.handle_login_and_logout", 
                      lambda func: func):
                result = await async_spacetrack_client.gp("25544")
        
        # Assert that get was called with the correct arguments
        assert mock_get.await_count == 2
        
        # Check the result
        assert isinstance(result, SpaceTrackGPResponse)
        assert result.NORAD_CAT_ID == 25544
        assert result.OBJECT_NAME == "ISS (ZARYA)"
        assert result.EPOCH == "2023-06-01T12:00:00"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test the context manager protocol."""
        with patch("orbittrack.spacetrack.aio.spacetrackaio.AsyncSpaceTrack.login", AsyncMock()) as mock_login:
            with patch("orbittrack.spacetrack.aio.spacetrackaio.AsyncSpaceTrack.close", AsyncMock()) as mock_close:
                async with AsyncSpaceTrack(username="test_user", password="test_pass") as client:
                    assert client is not None
                
                # Assert that login and close were called
                mock_login.assert_awaited_once()
                mock_close.assert_awaited_once()

# Additional test methods would be added for more functionality
