# Standard imports
from unittest.mock import Mock, patch

import pytest

# Django imports
from django.contrib.auth import get_user_model

# Strawberry/GraphQL imports
from gqlauth.core.types_ import GQLAuthError
from strawberry.types import Info

# Project imports
from server.campaigns.schema import CampaignQuery
from server.places.models import District, Province

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


@pytest.mark.django_db
class TestMeasurementsQuery:
    """Test measurements query"""

    @patch("server.campaigns.schema.get_user")
    def test_measurements_returns_all_measurements(
        self, mock_get_user, authenticated_info, measurement
    ):
        """Test that measurements query returns all measurements"""
        mock_get_user.return_value = authenticated_info.context.request.user

        query = CampaignQuery()
        result = query.measurements(authenticated_info)

        assert len(result) == 1
        assert result[0].name == "measurement_001.txt"

    @patch("server.campaigns.schema.get_user")
    def test_measurements_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, measurement
    ):
        """Test that unauthenticated user cannot query measurements"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.measurements(unauthenticated_info)

    @patch("server.campaigns.schema.get_user")
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

    @patch("server.campaigns.schema.get_user")
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

    @patch("server.campaigns.schema.get_user")
    def test_districts_unauthenticated_raises_error(
        self, mock_get_user, unauthenticated_info, district
    ):
        """Test that unauthenticated user cannot query districts"""
        mock_get_user.return_value = unauthenticated_info.context.request.user

        query = CampaignQuery()
        with pytest.raises(GQLAuthError):
            query.districts(unauthenticated_info)

    @patch("server.campaigns.schema.get_user")
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
