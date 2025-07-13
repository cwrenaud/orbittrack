"""
OrbitTrack SpaceTrack API module
"""

from orbittrack.spacetrack.exceptions import (
    SpaceTrackAuthenticationError,
    SpaceTrackRateLimitError,
)

__all__ = [
    "SpaceTrackAuthenticationError",
    "SpaceTrackRateLimitError",
]
