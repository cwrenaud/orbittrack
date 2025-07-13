"""
Tests for the SpaceTrack models.
"""

import pytest

from orbittrack.spacetrack.models import SpaceTrackBaseModel, SpaceTrackGPResponse


class TestSpaceTrackModels:
    """
    Tests for the SpaceTrack models.
    """

    def test_base_model_initialization(self):
        """Test that SpaceTrackBaseModel initializes correctly."""
        model = SpaceTrackBaseModel(status_code=200)
        
        assert model.status_code == 200
        
    def test_base_model_extra_fields(self):
        """Test that SpaceTrackBaseModel accepts extra fields."""
        model = SpaceTrackBaseModel(status_code=200, extra_field="test")
        
        assert model.status_code == 200
        # Access via the model's attribute
        assert model.extra_field == "test"
        # Access via dict representation
        assert model.model_dump()["extra_field"] == "test"
        
    def test_gp_response_initialization(self):
        """Test that SpaceTrackGPResponse initializes correctly."""
        model = SpaceTrackGPResponse(
            status_code=200,
            NORAD_CAT_ID=25544,
            OBJECT_NAME="ISS (ZARYA)",
            EPOCH="2023-06-01T12:00:00",
            MEAN_MOTION=15.5,
            ECCENTRICITY=0.0001,
            INCLINATION=51.6,
            RA_OF_ASC_NODE=247.4,
            ARG_OF_PERICENTER=130.5,
            MEAN_ANOMALY=325.9,
        )
        
        assert model.status_code == 200
        assert model.NORAD_CAT_ID == 25544
        assert model.OBJECT_NAME == "ISS (ZARYA)"
        assert model.EPOCH == "2023-06-01T12:00:00"
        assert model.MEAN_MOTION == 15.5
        assert model.ECCENTRICITY == 0.0001
        assert model.INCLINATION == 51.6
        assert model.RA_OF_ASC_NODE == 247.4
        assert model.ARG_OF_PERICENTER == 130.5
        assert model.MEAN_ANOMALY == 325.9
        
    def test_gp_response_partial_initialization(self):
        """Test that SpaceTrackGPResponse works with partial data."""
        # Only a few fields provided, others default to None
        model = SpaceTrackGPResponse(
            status_code=200,
            NORAD_CAT_ID=25544,
            OBJECT_NAME="ISS (ZARYA)",
        )
        
        assert model.status_code == 200
        assert model.NORAD_CAT_ID == 25544
        assert model.OBJECT_NAME == "ISS (ZARYA)"
        assert model.EPOCH is None
        assert model.MEAN_MOTION is None
