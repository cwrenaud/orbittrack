"""
Tests for the SpaceTrack client.
"""
from unittest.mock import MagicMock, patch
from collections.abc import Mapping

import httpx
import pytest

from orbittrack.spacetrack.exceptions import (
    SpaceTrackAuthenticationError,
    SpaceTrackRateLimitExceededError,
)
from orbittrack.spacetrack.models import SpaceTrackGPResponse
from orbittrack.spacetrack.spacetrack import SpaceTrack


class TestSpaceTrack:
    """
    Tests for the synchronous SpaceTrack client.
    """

    def test_initialization(self):
        """Test that the SpaceTrack client initializes correctly."""
        client = SpaceTrack(username="test_user", password="test_pass")
        
        assert client.base_url == "https://www.space-track.org"
        assert client.username == "test_user"
        assert client.password == "test_pass"
        assert not client.authenticated
        assert isinstance(client.http_client, httpx.Client)
        
        # Clean up resources
        client.close()

    @patch("httpx.Client.post")
    def test_login_success(self, mock_post, spacetrack_client):
        """Test successful login."""
        # Mock the response
        # mock_response = MagicMock()
        # mock_response.status_code = 200
        # mock_response.json.return_value = {"Login": "Success"}
        # mock_post.return_value = mock_response
        
        # Call login
        spacetrack_client.login()
        
        # Assert that post was called with the correct arguments
        mock_post.assert_called_once_with("/ajaxauth/login", data={
            "identity": "test_user",
            "password": "test_pass"
        })
        
        # Assert that the client is now authenticated
        assert spacetrack_client.authenticated

    @patch("httpx.Client.post")
    def test_login_failure(self, mock_post, spacetrack_client):
        """Test login failure."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Login": "Failed"}
        mock_post.return_value = mock_response
        
        # Call login and assert it raises the correct exception
        with pytest.raises(SpaceTrackAuthenticationError):
            spacetrack_client.login()
        
        # Assert that the client is not authenticated
        assert not spacetrack_client.authenticated

    @patch("httpx.Client.get")
    def test_logout(self, mock_get, spacetrack_client):
        """Test logout."""
        # Set the client as authenticated
        spacetrack_client._authenticated = True
        
        # Call logout
        spacetrack_client.logout()
        
        # Assert that get was called with the correct arguments
        mock_get.assert_called_once_with("/ajaxauth/logout")
        
        # Assert that the client is no longer authenticated
        assert not spacetrack_client.authenticated

    @patch("orbittrack.spacetrack.spacetrackutils.SpaceTrackUtils.set_minute_rate_limit")
    def test_set_minute_rate_limit(self, mock_set_limit, spacetrack_client):
        """Test setting the minute rate limit."""
        # Call the method
        spacetrack_client.set_minute_rate_limit("20/minute")
        
        # Assert that the method was called with the correct arguments
        mock_set_limit.assert_called_once()
        assert mock_set_limit.call_args[0][0].amount == 20
        
    @patch("orbittrack.spacetrack.spacetrackutils.SpaceTrackUtils.set_minute_rate_limit")
    def test_set_minute_rate_limit_exceeded(self, mock_set_limit, spacetrack_client):
        """Test that setting a minute rate limit that exceeds the default raises an exception."""
        # Set the mock to raise an exception
        mock_set_limit.side_effect = SpaceTrackRateLimitExceededError("Rate limit exceeded")
        
        # Call the method and assert it raises the correct exception
        with pytest.raises(SpaceTrackRateLimitExceededError):
            spacetrack_client.set_minute_rate_limit("100/minute")

    @patch("httpx.Client.get")
    def test_gp(self, mock_get, spacetrack_client):
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
        spacetrack_client._authenticated = True
        
        # Call the method with mocked rate limiter
        with patch("orbittrack.spacetrack.spacetrackutils.SpaceTrackUtils.ratelimit", lambda func: func):
            result = spacetrack_client.gp_session("25544")
        
        # Assert that get was called with the correct arguments
        mock_get.assert_called_once()
        
        # Check the result
        assert isinstance(result, SpaceTrackGPResponse)
        assert result.NORAD_CAT_ID == 25544
        assert result.OBJECT_NAME == "ISS (ZARYA)"
        assert result.EPOCH == "2023-06-01T12:00:00"


# Additional test classes would be added for AsyncSpaceTrack, SpaceTrackUtils, AsyncSpaceTrackUtils, etc.
