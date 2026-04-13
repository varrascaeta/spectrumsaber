# Standard imports
from datetime import datetime, timezone

import pytest

# Project imports
from server.campaigns.models import (
    Campaign,
    Category,
    CategoryType,
    Coverage,
    DataPoint,
    Measurement,
)
from server.places.models import Country, District, Province


@pytest.fixture
def country():
    """Create a test country"""
    return Country.objects.create(name="Argentina")


@pytest.fixture
def province(country):
    """Create a test province"""
    return Province.objects.create(name="Córdoba", country=country)


@pytest.fixture
def district(province):
    """Create a test district"""
    return District.objects.create(
        name="Test District", code="TEST001", province=province
    )


@pytest.fixture
def coverage():
    """Create a test coverage"""
    return Coverage.objects.create(name="Test Coverage", path="/test/coverage")


@pytest.fixture
def campaign(coverage, district):
    """Create a test campaign"""
    return Campaign.objects.create(
        name="Test Campaign",
        path="/test/coverage/campaign",
        coverage=coverage,
        district=district,
        date=datetime(2025, 1, 15, tzinfo=timezone.utc),
        external_id="EXT123",
        metadata={"geo_code": "TEST001"},
    )


@pytest.fixture
def data_point(campaign):
    """Create a test data point"""
    return DataPoint.objects.create(
        name="Point 001",
        path="/test/coverage/campaign/point001",
        campaign=campaign,
        order=1,
        latitude=-31.4201,
        longitude=-64.1888,
    )


@pytest.fixture
def category():
    """Create a test category"""
    return Category.objects.create(name=CategoryType.RADIANCE)


@pytest.fixture
def measurement(data_point, category):
    """Create a test measurement"""
    return Measurement.objects.create(
        name="measurement_001.txt",
        path="/test/coverage/campaign/point001/radiancia/measurement_001.txt",
        data_point=data_point,
        category=category,
    )
