"""
OrbitTrack SpaceTrack Models
"""
from typing import Optional

from pydantic import BaseModel

# ============================================
# SpaceTrack Response Models
# ============================================


class SpaceTrackBaseModel(BaseModel):
    """
    Base model for SpaceTrack data.
    """

    status_code: Optional[int] = None

    model_config = {
        "extra": "allow",  # Accept extra fields not defined in the model
        "populate_by_name": True,  # Allow using field names for population
        "use_enum_values": True,  # Use enum values instead of enum objects
        "json_encoders": {
            # Add custom encoders if needed
        },
    }


class SpaceTrackGPResponse(SpaceTrackBaseModel):
    """
    Model for SpaceTrack GP responses.
    """

    CCSDS_OMM_VERS: Optional[str] = None
    COMMENT: Optional[str] = None
    CREATION_DATE: Optional[str] = None
    ORIGINATOR: Optional[str] = None
    OBJECT_NAME: Optional[str] = None
    OBJECT_ID: Optional[str] = None
    CENTER_NAME: Optional[str] = None
    REF_FRAME: Optional[str] = None
    TIME_SYSTEM: Optional[str] = None
    MEAN_ELEMENT_THEORY: Optional[str] = None
    EPOCH: Optional[str] = None
    MEAN_MOTION: Optional[float] = None
    ECCENTRICITY: Optional[float] = None
    INCLINATION: Optional[float] = None
    RA_OF_ASC_NODE: Optional[float] = None
    ARG_OF_PERICENTER: Optional[float] = None
    MEAN_ANOMALY: Optional[float] = None
    EPHEMERIS_TYPE: Optional[int] = None
    CLASSIFICATION_TYPE: Optional[str] = None
    NORAD_CAT_ID: Optional[int] = None
    ELEMENT_SET_NO: Optional[int] = None
    REV_AT_EPOCH: Optional[int] = None
    BSTAR: Optional[float] = None
    MEAN_MOTION_DOT: Optional[float] = None
    MEAN_MOTION_DDOT: Optional[float] = None
    SEMIMAJOR_AXIS: Optional[float] = None
    PERIOD: Optional[float] = None
    APOAPSIS: Optional[float] = None
    PERIAPSIS: Optional[float] = None
    OBJECT_TYPE: Optional[str] = None
    RCS_SIZE: Optional[str] = None
    COUNTRY_CODE: Optional[str] = None
    LAUNCH_DATE: Optional[str] = None
    SITE: Optional[str] = None
    DECAY_DATE: Optional[str] = None
    FILE: Optional[str] = None
    GP_ID: Optional[int] = None
    TLE_LINE0: Optional[str] = None
    TLE_LINE1: Optional[str] = None
    TLE_LINE2: Optional[str] = None


class SpaceTrackAnnouncementResponse(SpaceTrackBaseModel):
    """
    Model for SpaceTrack announcement responses.
    """

    announcement_type: Optional[str] = None
    announcement_text: Optional[str] = None
    announcement_start: Optional[str] = None
    announcement_end: Optional[str] = None
