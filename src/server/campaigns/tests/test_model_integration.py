# Standard imports
import pytest

# Project imports
from server.campaigns.models import (
    PARENT_MAP,
    PATH_LEVELS_MODELS,
    Campaign,
    Category,
    CategoryType,
    DataPoint,
    Measurement,
)


@pytest.mark.django_db
class TestModelConstants:
    """Test model constants and mappings"""

    def test_path_levels_models(self):
        """Test PATH_LEVELS_MODELS mapping"""
        assert PATH_LEVELS_MODELS["coverage"] == "Coverage"
        assert PATH_LEVELS_MODELS["campaign"] == "Campaign"
        assert PATH_LEVELS_MODELS["data_point"] == "DataPoint"
        assert PATH_LEVELS_MODELS["category"] == "Category"
        assert PATH_LEVELS_MODELS["measurement"] == "Measurement"
        assert PATH_LEVELS_MODELS["complimentary_data"] == "ComplimentaryData"

    def test_parent_map(self):
        """Test PARENT_MAP mapping"""
        assert PARENT_MAP["campaign"] == ("Coverage", "coverage_id")
        assert PARENT_MAP["data_point"] == ("Campaign", "campaign_id")
        assert PARENT_MAP["measurement"] == ("DataPoint", "data_point_id")
        assert PARENT_MAP["complimentary_data"] == ("Campaign", "campaign_id")


@pytest.mark.django_db
class TestGraphQLTypesIntegration:
    """Integration tests for GraphQL types with real data"""

    def test_coverage_type_with_campaigns_relationship(
        self, coverage, campaign
    ):
        """Test CoverageType with campaigns relationship"""
        assert coverage.id is not None
        assert coverage.name == "Test Coverage"
        campaigns = Campaign.objects.filter(coverage=coverage)
        assert campaigns.count() == 1
        assert campaigns.first().name == "Test Campaign"

    def test_campaign_type_with_all_relationships(
        self, campaign, coverage, district, data_point
    ):
        """Test CampaignType with all relationships"""
        assert campaign.coverage_id == coverage.id
        assert campaign.district_id == district.id
        data_points = DataPoint.objects.filter(campaign=campaign)
        assert data_points.count() == 1

    def test_datapoint_type_with_measurements(
        self, data_point, measurement, campaign
    ):
        """Test DataPointType with measurements relationship"""
        assert data_point.campaign_id == campaign.id
        measurements = Measurement.objects.filter(data_point=data_point)
        assert measurements.count() == 1
        assert measurements.first().name == "measurement_001.txt"

    def test_measurement_type_with_category(
        self, measurement, category, data_point
    ):
        """Test MeasurementType with category relationship"""
        assert measurement.category_id == category.id
        assert measurement.data_point_id == data_point.id
        assert measurement.category.name == CategoryType.RADIANCE

    def test_district_type_with_campaigns(self, district, campaign):
        """Test DistrictType with campaigns relationship"""
        campaigns = Campaign.objects.filter(district=district)
        assert campaigns.count() == 1
        assert campaigns.first().external_id == "EXT123"

    def test_category_type_with_multiple_measurements(
        self, category, data_point, measurement
    ):
        """Test CategoryType can have multiple measurements"""
        # Create another measurement with same category
        measurement2 = Measurement.objects.create(
            name="measurement_002.txt",
            path=(
                "/test/coverage/campaign/point001/radiancia/"
                "measurement_002.txt"
            ),
            data_point=data_point,
            category=category,
        )

        measurements = Measurement.objects.filter(category=category)
        assert measurements.count() == 2
        assert measurement in measurements
        assert measurement2 in measurements

    def test_campaign_metadata_field(self, campaign):
        """Test that campaign metadata field is accessible"""
        assert campaign.metadata is not None
        assert isinstance(campaign.metadata, dict)
        assert campaign.metadata.get("geo_code") == "TEST001"

    def test_full_hierarchy_structure(
        self, coverage, campaign, data_point, measurement, category, district
    ):
        """Test complete hierarchy from coverage to measurement"""
        # Verify full chain
        assert measurement.data_point == data_point
        assert data_point.campaign == campaign
        assert campaign.coverage == coverage
        assert campaign.district == district
        assert measurement.category == category

        # Verify reverse relationships work
        assert coverage.campaigns.filter(id=campaign.id).exists()
        assert campaign.data_points.filter(id=data_point.id).exists()
        assert data_point.measurements.filter(id=measurement.id).exists()
