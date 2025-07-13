"""
Tests for the SpaceTrack exceptions.
"""
from orbittrack.spacetrack.exceptions import (
    SpaceTrackAuthenticationError,
    SpaceTrackBaseException,
    SpaceTrackHttpxTimeoutError,
    SpaceTrackRaiseStatusError,
    SpaceTrackRateLimitError,
    SpaceTrackRateLimitExceededError,
    SpaceTrackRequestError,
    SpaceTrackTimeoutError,
)


class TestExceptions:
    """
    Tests for the SpaceTrack exception classes.
    """

    def test_base_exception(self):
        """Test that SpaceTrackBaseException is a subclass of Exception."""
        assert issubclass(SpaceTrackBaseException, Exception)

        # Create an instance with a message
        exception = SpaceTrackBaseException("Test message")
        assert str(exception) == "Test message"

    def test_authentication_error(self):
        """Test that SpaceTrackAuthenticationError is a subclass of SpaceTrackBaseException."""
        assert issubclass(SpaceTrackAuthenticationError, SpaceTrackBaseException)

        # Create an instance with a message
        exception = SpaceTrackAuthenticationError("Authentication failed")
        assert str(exception) == "Authentication failed"

    def test_rate_limit_error(self):
        """Test that SpaceTrackRateLimitError is a subclass of SpaceTrackBaseException."""
        assert issubclass(SpaceTrackRateLimitError, SpaceTrackBaseException)

        # Create an instance with a message
        exception = SpaceTrackRateLimitError("Rate limit exceeded")
        assert str(exception) == "Rate limit exceeded"

    def test_rate_limit_exceeded_error(self):
        """Test that SpaceTrackRateLimitExceededError is a subclass of SpaceTrackBaseException."""
        assert issubclass(SpaceTrackRateLimitExceededError, SpaceTrackBaseException)

        # Create an instance with a message
        exception = SpaceTrackRateLimitExceededError("Rate limit configuration exceeded defaults")
        assert str(exception) == "Rate limit configuration exceeded defaults"

    def test_request_error(self):
        """Test that SpaceTrackRequestError is a subclass of SpaceTrackBaseException."""
        assert issubclass(SpaceTrackRequestError, SpaceTrackBaseException)

        # Create an instance with a message
        exception = SpaceTrackRequestError("Request failed")
        assert str(exception) == "Request failed"

    def test_timeout_error(self):
        """Test that SpaceTrackTimeoutError is a subclass of SpaceTrackBaseException."""
        assert issubclass(SpaceTrackTimeoutError, SpaceTrackBaseException)

        # Create an instance with a message
        exception = SpaceTrackTimeoutError("Request timed out")
        assert str(exception) == "Request timed out"

    def test_httpx_timeout_error(self):
        """Test that SpaceTrackHttpxTimeoutError is a subclass of SpaceTrackBaseException."""
        assert issubclass(SpaceTrackHttpxTimeoutError, SpaceTrackBaseException)

        # Create an instance with a message
        exception = SpaceTrackHttpxTimeoutError("HTTPX timeout occurred")
        assert str(exception) == "HTTPX timeout occurred"

    def test_raise_status_error(self):
        """Test that SpaceTrackRaiseStatusError is a subclass of SpaceTrackBaseException."""
        assert issubclass(SpaceTrackRaiseStatusError, SpaceTrackBaseException)

        # Create an instance with a message
        exception = SpaceTrackRaiseStatusError("HTTP status error")
        assert str(exception) == "HTTP status error"
