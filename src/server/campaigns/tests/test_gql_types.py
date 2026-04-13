# Standard imports
import pytest

# Django imports
from django.contrib.auth import get_user_model

# Project imports
from server.campaigns.gql_types import (
    CampaignFilter,
    CampaignType,
    CategoryFilter,
    CategoryType,
    CoverageFilter,
    CoverageType,
    DataPointFilter,
    DataPointType,
    DistrictFilter,
    DistrictType,
    MeasurementFilter,
    MeasurementType,
)

User = get_user_model()


@pytest.mark.django_db
class TestCoverageFilter:
    """Test CoverageFilter"""

    @pytest.mark.parametrize("field", ["id", "name"])
    def test_coverage_filter_has_field(self, field):
        """Test that CoverageFilter has required fields"""
        assert hasattr(CoverageFilter, "__annotations__")
        assert field in CoverageFilter.__annotations__

    def test_coverage_filter_meta_lookups(self):
        """Test that CoverageFilter has lookups enabled"""
        assert hasattr(CoverageFilter, "Meta")
        assert hasattr(CoverageFilter.Meta, "lookups")
        assert CoverageFilter.Meta.lookups is True


@pytest.mark.django_db
class TestCampaignFilter:
    """Test CampaignFilter"""

    @pytest.mark.parametrize(
        "field", ["id", "name", "date", "external_id", "district", "coverage"]
    )
    def test_campaign_filter_has_field(self, field):
        """Test that CampaignFilter has required fields"""
        assert field in CampaignFilter.__annotations__

    def test_campaign_filter_meta_lookups(self):
        """Test that CampaignFilter has lookups enabled"""
        assert hasattr(CampaignFilter, "Meta")
        assert CampaignFilter.Meta.lookups is True


@pytest.mark.django_db
class TestCategoryFilter:
    """Test CategoryFilter"""

    @pytest.mark.parametrize("field", ["id", "name"])
    def test_category_filter_has_field(self, field):
        """Test that CategoryFilter has required fields"""
        assert field in CategoryFilter.__annotations__

    def test_category_filter_meta_lookups(self):
        """Test that CategoryFilter has lookups enabled"""
        assert hasattr(CategoryFilter, "Meta")
        assert CategoryFilter.Meta.lookups is True


@pytest.mark.django_db
class TestDataPointFilter:
    """Test DataPointFilter"""

    @pytest.mark.parametrize("field", ["id", "name", "campaign"])
    def test_datapoint_filter_has_field(self, field):
        """Test that DataPointFilter has required fields"""
        assert field in DataPointFilter.__annotations__

    def test_datapoint_filter_meta_lookups(self):
        """Test that DataPointFilter has lookups enabled"""
        assert hasattr(DataPointFilter, "Meta")
        assert DataPointFilter.Meta.lookups is True


@pytest.mark.django_db
class TestMeasurementFilter:
    """Test MeasurementFilter"""

    @pytest.mark.parametrize("field", ["id", "name", "category", "data_point"])
    def test_measurement_filter_has_field(self, field):
        """Test that MeasurementFilter has required fields"""
        assert field in MeasurementFilter.__annotations__

    def test_measurement_filter_meta_lookups(self):
        """Test that MeasurementFilter has lookups enabled"""
        assert hasattr(MeasurementFilter, "Meta")
        assert MeasurementFilter.Meta.lookups is True


@pytest.mark.django_db
class TestDistrictFilter:
    """Test DistrictFilter"""

    @pytest.mark.parametrize("field", ["id", "name"])
    def test_district_filter_has_field(self, field):
        """Test that DistrictFilter has required fields"""
        assert field in DistrictFilter.__annotations__

    def test_district_filter_meta_lookups(self):
        """Test that DistrictFilter has lookups enabled"""
        assert hasattr(DistrictFilter, "Meta")
        assert DistrictFilter.Meta.lookups is True


@pytest.mark.django_db
class TestDistrictType:
    """Test DistrictType"""

    @pytest.mark.parametrize("field", ["id", "name", "campaigns"])
    def test_district_type_has_field(self, field):
        """Test that DistrictType has required fields"""
        assert field in DistrictType.__annotations__


@pytest.mark.django_db
class TestCoverageType:
    """Test CoverageType"""

    @pytest.mark.parametrize("field", ["id", "name", "campaigns"])
    def test_coverage_type_has_field(self, field):
        """Test that CoverageType has required fields"""
        assert field in CoverageType.__annotations__


@pytest.mark.django_db
class TestCampaignType:
    """Test CampaignType"""

    @pytest.mark.parametrize(
        "field",
        [
            "id",
            "name",
            "date",
            "external_id",
            "metadata",
            "district",
            "coverage",
            "data_points",
        ],
    )
    def test_campaign_type_has_field(self, field):
        """Test that CampaignType has required fields"""
        assert field in CampaignType.__annotations__


@pytest.mark.django_db
class TestDataPointType:
    """Test DataPointType"""

    @pytest.mark.parametrize(
        "field", ["id", "name", "campaign", "measurements"]
    )
    def test_datapoint_type_has_field(self, field):
        """Test that DataPointType has required fields"""
        assert field in DataPointType.__annotations__


@pytest.mark.django_db
class TestCategoryType:
    """Test CategoryType GraphQL type"""

    @pytest.mark.parametrize("field", ["id", "name", "campaigns"])
    def test_category_type_has_field(self, field):
        """Test that CategoryType has required fields"""
        assert field in CategoryType.__annotations__


@pytest.mark.django_db
class TestMeasurementType:
    """Test MeasurementType"""

    @pytest.mark.parametrize("field", ["id", "name", "category", "data_point"])
    def test_measurement_type_has_field(self, field):
        """Test that MeasurementType has required fields"""
        assert field in MeasurementType.__annotations__
