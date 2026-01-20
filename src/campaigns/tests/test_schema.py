# Standard imports
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

# Django imports
from django.contrib.auth import get_user_model

# Strawberry/GraphQL imports
from gqlauth.core.types_ import GQLAuthError
from strawberry.types import Info

# Project imports
from src.campaigns.models import (
    Campaign,
    Category,
    CategoryType as CategoryTypeModel,
    Coverage,
    DataPoint,
    Measurement,
)
from src.campaigns.schema import CampaignQuery
from src.places.models import Country, District, Province

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user"""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def authenticated_info(user):
    """Create mock Info with authenticated user"""
    info = Mock(spec=Info)
    info.context = Mock()
    info.context.request = Mock()
    info.context.request.user = user
    return info


@pytest.fixture
def unauthenticated_info():
    """Create mock Info with unauthenticated user"""
    info = Mock(spec=Info)
    info.context = Mock()
    info.context.request = Mock()
    info.context.request.user = Mock()
    info.context.request.user.is_authenticated = False
    return info


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
def coverage2():
    """Create a second test coverage"""
    return Coverage.objects.create(
        name="Test Coverage 2", path="/test/coverage2"
    )


@pytest.fixture
def campaign(coverage, district):
    """Create a test campaign"""
    return Campaign.objects.create(
        name="Test Campaign",
        path="/test/coverage/campaign",
        coverage=coverage,
        district=district,
        date=datetime(2025, 1, 15),
        external_id="EXT123",
        metadata={"geo_code": "TEST001"},
    )


@pytest.fixture
def campaign2(coverage2, district):
    """Create a second test campaign"""
    return Campaign.objects.create(
        name="Test Campaign 2",
        path="/test/coverage2/campaign2",
        coverage=coverage2,
        district=district,
        date=datetime(2025, 2, 20),
        external_id="EXT456",
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
    return Category.objects.create(name=CategoryTypeModel.RADIANCE)


@pytest.fixture
def measurement(data_point, category):
    """Create a test measurement"""
    return Measurement.objects.create(
        name="measurement_001.txt",
        path=(
            "/test/coverage/campaign/point001/radiancia/" "measurement_001.txt"
        ),
        data_point=data_point,
        category=category,
    )


@pytest.mark.django_db
class TestCoveragesQuery:
    """Test coverages query"""

    @patch("src.campaigns.schema.get_user")
    def test_coverages_returns_all_coverages(
        self, mock_get_user, authenticated_info, coverage, coverage2
    ):
        """Test that coverages query returns all coverages"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.coverages(authenticated_info)

        assert len(result) == 2
        coverage_names = [c.name for c in result]
        assert "Test Coverage" in coverage_names
        assert "Test Coverage 2" in coverage_names

    @patch("src.campaigns.schema.get_user")
    def test_coverages_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, coverage
    ):
        """Test that unauthenticated user cannot query coverages"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.coverages(unauthenticated_info)

    @patch("src.campaigns.schema.get_user")
    def test_coverages_with_filter(
        self, mock_get_user, authenticated_info, coverage, coverage2
    ):
        """Test coverages query with filter"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        # Test without filter implementation (just verify it doesn't crash)
        result = query.coverages(authenticated_info, filters=None)
        assert len(result) >= 2


@pytest.mark.django_db
class TestCampaignsQuery:
    """Test campaigns query"""

    @patch("src.campaigns.schema.get_user")
    def test_campaigns_returns_all_campaigns(
        self, mock_get_user, authenticated_info, campaign, campaign2
    ):
        """Test that campaigns query returns all campaigns"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.campaigns(authenticated_info)

        assert len(result) == 2
        campaign_names = [c.name for c in result]
        assert "Test Campaign" in campaign_names
        assert "Test Campaign 2" in campaign_names

    @patch("src.campaigns.schema.get_user")
    def test_campaigns_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, campaign
    ):
        """Test that unauthenticated user cannot query campaigns"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.campaigns(unauthenticated_info)

    @patch("src.campaigns.schema.get_user")
    def test_campaigns_with_relationships(
        self,
        mock_get_user,
        authenticated_info,
        campaign,
        coverage,
        district,
    ):
        """Test campaigns query includes relationships"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.campaigns(authenticated_info)

        assert len(result) == 1
        campaign_obj = result[0]
        assert campaign_obj.coverage_id == coverage.id
        assert campaign_obj.district_id == district.id


@pytest.mark.django_db
class TestDataPointsQuery:
    """Test data_points query"""

    @patch("src.campaigns.schema.get_user")
    def test_data_points_returns_all_data_points(
        self, mock_get_user, authenticated_info, data_point
    ):
        """Test that data_points query returns all data points"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.data_points(authenticated_info)

        assert len(result) == 1
        assert result[0].name == "Point 001"
        assert result[0].order == 1

    @patch("src.campaigns.schema.get_user")
    def test_data_points_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, data_point
    ):
        """Test that unauthenticated user cannot query data_points"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.data_points(unauthenticated_info)

    @patch("src.campaigns.schema.get_user")
    def test_data_points_with_campaign_relationship(
        self, mock_get_user, authenticated_info, data_point, campaign
    ):
        """Test data_points query includes campaign relationship"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.data_points(authenticated_info)

        assert len(result) == 1
        assert result[0].campaign_id == campaign.id


@pytest.mark.django_db
class TestCategoriesQuery:
    """Test categories query"""

    @patch("src.campaigns.schema.get_user")
    def test_categories_returns_all_categories(
        self, mock_get_user, authenticated_info, category
    ):
        """Test that categories query returns all categories"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.categories(authenticated_info)

        assert len(result) == 1
        assert result[0].name == CategoryTypeModel.RADIANCE

    @patch("src.campaigns.schema.get_user")
    def test_categories_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, category
    ):
        """Test that unauthenticated user cannot query categories"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.categories(unauthenticated_info)

    @patch("src.campaigns.schema.get_user")
    def test_categories_multiple(
        self, mock_get_user, authenticated_info, category
    ):
        """Test categories query with multiple categories"""
        # Create another category
        Category.objects.create(name=CategoryTypeModel.REFLECTANCE)

        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.categories(authenticated_info)

        assert len(result) == 2
        category_names = [c.name for c in result]
        assert CategoryTypeModel.RADIANCE in category_names
        assert CategoryTypeModel.REFLECTANCE in category_names


@pytest.mark.django_db
class TestMeasurementsQuery:
    """Test measurements query"""

    @patch("src.campaigns.schema.get_user")
    def test_measurements_returns_all_measurements(
        self, mock_get_user, authenticated_info, measurement
    ):
        """Test that measurements query returns all measurements"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.measurements(authenticated_info)

        assert len(result) == 1
        assert result[0].name == "measurement_001.txt"

    @patch("src.campaigns.schema.get_user")
    def test_measurements_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, measurement
    ):
        """Test that unauthenticated user cannot query measurements"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.measurements(unauthenticated_info)

    @patch("src.campaigns.schema.get_user")
    def test_measurements_with_relationships(
        self,
        mock_get_user,
        authenticated_info,
        measurement,
        data_point,
        category,
    ):
        """Test measurements query includes relationships"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.measurements(authenticated_info)

        assert len(result) == 1
        measurement_obj = result[0]
        assert measurement_obj.data_point_id == data_point.id
        assert measurement_obj.category_id == category.id


@pytest.mark.django_db
class TestDistrictsQuery:
    """Test districts query"""

    @patch("src.campaigns.schema.get_user")
    def test_districts_returns_all_districts(
        self, mock_get_user, authenticated_info, district
    ):
        """Test that districts query returns all districts"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.districts(authenticated_info)

        assert len(result) == 1
        assert result[0].name == "Test District"
        assert result[0].code == "TEST001"

    @patch("src.campaigns.schema.get_user")
    def test_districts_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, district
    ):
        """Test that unauthenticated user cannot query districts"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.districts(unauthenticated_info)

    @patch("src.campaigns.schema.get_user")
    def test_districts_multiple(
        self, mock_get_user, authenticated_info, district, province
    ):
        """Test districts query with multiple districts"""
        # Create another district
        District.objects.create(
            name="Another District", code="TEST002", province=province
        )

        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.districts(authenticated_info)

        assert len(result) == 2
        district_names = [d.name for d in result]
        assert "Test District" in district_names
        assert "Another District" in district_names


@pytest.mark.django_db
class TestCampaignQueryIntegration:
    """Integration tests for CampaignQuery"""

    @patch("src.campaigns.schema.get_user")
    def test_full_data_hierarchy(
        self,
        mock_get_user,
        authenticated_info,
        coverage,
        campaign,
        data_point,
        measurement,
        category,
        district,
    ):
        """Test querying full data hierarchy"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()

        # Query each level and verify relationships
        coverages = query.coverages(authenticated_info)
        assert len(coverages) == 1

        campaigns = query.campaigns(authenticated_info)
        assert len(campaigns) == 1
        assert campaigns[0].coverage_id == coverage.id

        data_points = query.data_points(authenticated_info)
        assert len(data_points) == 1
        assert data_points[0].campaign_id == campaign.id

        measurements = query.measurements(authenticated_info)
        assert len(measurements) == 1
        assert measurements[0].data_point_id == data_point.id
        assert measurements[0].category_id == category.id

    @patch("src.campaigns.schema.get_user")
    def test_query_empty_results(self, mock_get_user, authenticated_info):
        """Test queries return empty lists when no data exists"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()

        assert len(query.coverages(authenticated_info)) == 0
        assert len(query.campaigns(authenticated_info)) == 0
        assert len(query.data_points(authenticated_info)) == 0
        assert len(query.categories(authenticated_info)) == 0
        assert len(query.measurements(authenticated_info)) == 0
        assert len(query.districts(authenticated_info)) == 0
