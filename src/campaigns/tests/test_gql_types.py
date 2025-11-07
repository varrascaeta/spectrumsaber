# Standard imports
import pytest

# Django imports
from django.contrib.auth import get_user_model

# Project imports
from src.campaigns.gql_types import (
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

    def test_coverage_filter_has_id(self):
        """Test that CoverageFilter has id field"""
        assert hasattr(CoverageFilter, "__annotations__")
        assert "id" in CoverageFilter.__annotations__

    def test_coverage_filter_has_name(self):
        """Test that CoverageFilter has name field"""
        assert "name" in CoverageFilter.__annotations__

    def test_coverage_filter_meta_lookups(self):
        """Test that CoverageFilter has lookups enabled"""
        assert hasattr(CoverageFilter, "Meta")
        assert hasattr(CoverageFilter.Meta, "lookups")
        assert CoverageFilter.Meta.lookups is True


@pytest.mark.django_db
class TestCampaignFilter:
    """Test CampaignFilter"""

    def test_campaign_filter_has_required_fields(self):
        """Test that CampaignFilter has all required fields"""
        annotations = CampaignFilter.__annotations__
        assert "id" in annotations
        assert "name" in annotations
        assert "date" in annotations
        assert "external_id" in annotations
        assert "district" in annotations
        assert "coverage" in annotations

    def test_campaign_filter_meta_lookups(self):
        """Test that CampaignFilter has lookups enabled"""
        assert hasattr(CampaignFilter, "Meta")
        assert CampaignFilter.Meta.lookups is True


@pytest.mark.django_db
class TestCategoryFilter:
    """Test CategoryFilter"""

    def test_category_filter_has_id_and_name(self):
        """Test that CategoryFilter has id and name fields"""
        annotations = CategoryFilter.__annotations__
        assert "id" in annotations
        assert "name" in annotations

    def test_category_filter_meta_lookups(self):
        """Test that CategoryFilter has lookups enabled"""
        assert hasattr(CategoryFilter, "Meta")
        assert CategoryFilter.Meta.lookups is True


@pytest.mark.django_db
class TestDataPointFilter:
    """Test DataPointFilter"""

    def test_datapoint_filter_has_required_fields(self):
        """Test that DataPointFilter has all required fields"""
        annotations = DataPointFilter.__annotations__
        assert "id" in annotations
        assert "name" in annotations
        assert "campaign" in annotations

    def test_datapoint_filter_meta_lookups(self):
        """Test that DataPointFilter has lookups enabled"""
        assert hasattr(DataPointFilter, "Meta")
        assert DataPointFilter.Meta.lookups is True


@pytest.mark.django_db
class TestMeasurementFilter:
    """Test MeasurementFilter"""

    def test_measurement_filter_has_required_fields(self):
        """Test that MeasurementFilter has all required fields"""
        annotations = MeasurementFilter.__annotations__
        assert "id" in annotations
        assert "name" in annotations
        assert "category" in annotations
        assert "data_point" in annotations

    def test_measurement_filter_meta_lookups(self):
        """Test that MeasurementFilter has lookups enabled"""
        assert hasattr(MeasurementFilter, "Meta")
        assert MeasurementFilter.Meta.lookups is True


@pytest.mark.django_db
class TestDistrictFilter:
    """Test DistrictFilter"""

    def test_district_filter_has_id_and_name(self):
        """Test that DistrictFilter has id and name fields"""
        annotations = DistrictFilter.__annotations__
        assert "id" in annotations
        assert "name" in annotations

    def test_district_filter_meta_lookups(self):
        """Test that DistrictFilter has lookups enabled"""
        assert hasattr(DistrictFilter, "Meta")
        assert DistrictFilter.Meta.lookups is True


@pytest.mark.django_db
class TestDistrictType:
    """Test DistrictType"""

    def test_district_type_has_required_fields(self):
        """Test that DistrictType has all required fields"""
        annotations = DistrictType.__annotations__
        assert "id" in annotations
        assert "name" in annotations
        assert "campaigns" in annotations


@pytest.mark.django_db
class TestCoverageType:
    """Test CoverageType"""

    def test_coverage_type_has_required_fields(self):
        """Test that CoverageType has all required fields"""
        annotations = CoverageType.__annotations__
        assert "id" in annotations
        assert "name" in annotations
        assert "campaigns" in annotations


@pytest.mark.django_db
class TestCampaignType:
    """Test CampaignType"""

    def test_campaign_type_has_required_fields(self):
        """Test that CampaignType has all required fields"""
        annotations = CampaignType.__annotations__
        assert "id" in annotations
        assert "name" in annotations
        assert "date" in annotations
        assert "external_id" in annotations
        assert "metadata" in annotations
        assert "district" in annotations
        assert "coverage" in annotations
        assert "data_points" in annotations


@pytest.mark.django_db
class TestDataPointType:
    """Test DataPointType"""

    def test_datapoint_type_has_required_fields(self):
        """Test that DataPointType has all required fields"""
        annotations = DataPointType.__annotations__
        assert "id" in annotations
        assert "name" in annotations
        assert "campaign" in annotations
        assert "measurements" in annotations


@pytest.mark.django_db
class TestCategoryType:
    """Test CategoryType GraphQL type"""

    def test_category_type_has_required_fields(self):
        """Test that CategoryType has all required fields"""
        annotations = CategoryType.__annotations__
        assert "id" in annotations
        assert "name" in annotations
        assert "campaigns" in annotations


@pytest.mark.django_db
class TestMeasurementType:
    """Test MeasurementType"""

    def test_measurement_type_has_required_fields(self):
        """Test that MeasurementType has all required fields"""
        annotations = MeasurementType.__annotations__
        assert "id" in annotations
        assert "name" in annotations
        assert "category" in annotations
        assert "data_point" in annotations
