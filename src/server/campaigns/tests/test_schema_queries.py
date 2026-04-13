# Standard imports
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

# Django imports
from django.contrib.auth import get_user_model

# Strawberry/GraphQL imports
from gqlauth.core.types_ import GQLAuthError
from strawberry.types import Info

# Project imports
from server.campaigns.models import (
    Campaign,
    Category,
)
from server.campaigns.models import CategoryType as CategoryTypeModel
from server.campaigns.models import (
    Coverage,
)
from server.campaigns.schema import CampaignQuery
from server.places.models import District

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
def coverage2():
    """Create a second test coverage"""
    return Coverage.objects.create(
        name="Test Coverage 2", path="/test/coverage2"
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


@pytest.mark.django_db
class TestCoveragesQuery:
    """Test coverages query"""

    @patch("server.campaigns.schema.get_user")
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

    @patch("server.campaigns.schema.get_user")
    def test_coverages_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, coverage
    ):
        """Test that unauthenticated user cannot query coverages"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.coverages(unauthenticated_info)

    @patch("server.campaigns.schema.get_user")
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

    @patch("server.campaigns.schema.get_user")
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

    @patch("server.campaigns.schema.get_user")
    def test_campaigns_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, campaign
    ):
        """Test that unauthenticated user cannot query campaigns"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.campaigns(unauthenticated_info)

    @patch("server.campaigns.schema.get_user")
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

    @patch("server.campaigns.schema.get_user")
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

    @patch("server.campaigns.schema.get_user")
    def test_data_points_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, data_point
    ):
        """Test that unauthenticated user cannot query data_points"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.data_points(unauthenticated_info)

    @patch("server.campaigns.schema.get_user")
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

    @patch("server.campaigns.schema.get_user")
    def test_categories_returns_all_categories(
        self, mock_get_user, authenticated_info, category
    ):
        """Test that categories query returns all categories"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.categories(authenticated_info)

        assert len(result) == 1
        assert result[0].name == CategoryTypeModel.RADIANCE

    @patch("server.campaigns.schema.get_user")
    def test_categories_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, category
    ):
        """Test that unauthenticated user cannot query categories"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.categories(unauthenticated_info)

    @patch("server.campaigns.schema.get_user")
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
