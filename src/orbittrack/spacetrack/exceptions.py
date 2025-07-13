"""Exceptions for SpaceTrack."""

# ===========================================
# SpaceTrack Base Exception
# ===========================================
class SpaceTrackBaseException(Exception):
    """Base exception for SpaceTrack errors."""

# ===========================================
# SpaceTrack Ratelimit Exceptions
# ===========================================
class SpaceTrackRateLimitError(SpaceTrackBaseException):
    """Exception raised when the SpaceTrack API rate limit is exceeded."""

class SpaceTrackRateLimitExceededError(SpaceTrackBaseException):
    """Exception raised when the SpaceTrack API rate limit is exceeded."""

    
# ===========================================
# SpaceTrack Httpx Async Exceptions
# ===========================================
class AsyncSpaceTrackRequestError(SpaceTrackBaseException):
    """Exception raised for httpx request errors"""
    
class AsyncSpaceTrackAsyncTimeoutError(SpaceTrackBaseException):
    """Exception raised for asyncio timeout error"""
    
class AsyncSpaceTrackHttpxTimeoutError(SpaceTrackBaseException):
    """Exception raised for httpx Timeout error"""
    
class AsyncSpaceTrackRaiseStatusError(SpaceTrackBaseException):
    """Exception rasied for httpx RaiseStatus error"""
    
# ===========================================
# SpaceTrack Httpx Exceptions
# ===========================================
class SpaceTrackRequestError(SpaceTrackBaseException):
    """Exception raised for httpx request errors"""
    
class SpaceTrackTimeoutError(SpaceTrackBaseException):
    """Exception raised for asyncio timeout error"""
    
class SpaceTrackHttpxTimeoutError(SpaceTrackBaseException):
    """Exception raised for httpx Timeout error"""
    
class SpaceTrackRaiseStatusError(SpaceTrackBaseException):
    """Exception rasied for httpx RaiseStatus error"""
    
# ===========================================
# SpaceTrack Authentication Exceptions
# ===========================================   
class SpaceTrackAuthenticationError(SpaceTrackBaseException):
    """Exception raised for authentication errors when accessing SpaceTrack."""


    
class SpaceTrackValidationError(SpaceTrackBaseException):
    """Exception raised for validation errors in SpaceTrack models."""

class SpaceTrackNotFoundError(SpaceTrackBaseException):
    """Exception raised when a SpaceTrack resource is not found."""

class SpaceTrackConnectionError(SpaceTrackBaseException):
    """Exception raised for connection errors when accessing SpaceTrack."""
    

    

