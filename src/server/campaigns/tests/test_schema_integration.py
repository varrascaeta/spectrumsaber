# Standard imports
from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest

# Django imports
from django.contrib.auth import get_user_model

# Strawberry/GraphQL imports
from strawberry.types import Info

# Project imports
from server.campaigns.models import Campaign
from server.campaigns.models import (
    Coverage,
)
from server.campaigns.schema import CampaignQuery

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
class TestCampaignQueryIntegration:
    """Integration tests for CampaignQuery"""

    @patch("server.campaigns.schema.get_user")
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

    @patch("server.campaigns.schema.get_user")
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


@pytest.mark.django_db
class TestFilterBranches:
    """Test that filter application branches are exercised."""

    @patch("server.campaigns.schema.get_user")
    def test_coverages_filter_branch(
        self, mock_get_user, authenticated_info, coverage
    ):
        from server.campaigns.gql_types import CoverageFilter

        mock_get_user.return_value = authenticated_info.context.request.user
        query = CampaignQuery()
        result = query.coverages(authenticated_info, filters=CoverageFilter())
        assert len(result) >= 1

    @patch("server.campaigns.schema.get_user")
    def test_campaigns_filter_branch(
        self, mock_get_user, authenticated_info, campaign
    ):
        from server.campaigns.gql_types import CampaignFilter

        mock_get_user.return_value = authenticated_info.context.request.user
        query = CampaignQuery()
        result = query.campaigns(authenticated_info, filters=CampaignFilter())
        assert len(result) >= 1

    @patch("server.campaigns.schema.get_user")
    def test_campaigns_date_gte_branch(
        self, mock_get_user, authenticated_info, campaign, campaign2
    ):
        mock_get_user.return_value = authenticated_info.context.request.user
        query = CampaignQuery()
        result = query.campaigns(
            authenticated_info, date_gte=date(2025, 2, 1)
        )
        assert len(result) == 1
        assert result[0].name == "Test Campaign 2"

    @patch("server.campaigns.schema.get_user")
    def test_campaigns_date_lte_branch(
        self, mock_get_user, authenticated_info, campaign, campaign2
    ):
        mock_get_user.return_value = authenticated_info.context.request.user
        query = CampaignQuery()
        result = query.campaigns(
            authenticated_info, date_lte=date(2025, 1, 31)
        )
        assert len(result) == 1
        assert result[0].name == "Test Campaign"

    @patch("server.campaigns.schema.get_user")
    def test_data_points_filter_branch(
        self, mock_get_user, authenticated_info, data_point
    ):
        from server.campaigns.gql_types import DataPointFilter

        mock_get_user.return_value = authenticated_info.context.request.user
        query = CampaignQuery()
        result = query.data_points(
            authenticated_info, filters=DataPointFilter()
        )
        assert len(result) >= 1

    @patch("server.campaigns.schema.get_user")
    def test_categories_filter_branch(
        self, mock_get_user, authenticated_info, category
    ):
        from server.campaigns.gql_types import CategoryFilter

        mock_get_user.return_value = authenticated_info.context.request.user
        query = CampaignQuery()
        result = query.categories(
            authenticated_info, filters=CategoryFilter()
        )
        assert len(result) >= 1

    @patch("server.campaigns.schema.get_user")
    def test_measurements_filter_branch(
        self, mock_get_user, authenticated_info, measurement
    ):
        from server.campaigns.gql_types import MeasurementFilter

        mock_get_user.return_value = authenticated_info.context.request.user
        query = CampaignQuery()
        result = query.measurements(
            authenticated_info, filters=MeasurementFilter()
        )
        assert len(result) >= 1

    @patch("server.campaigns.schema.get_user")
    def test_districts_filter_branch(
        self, mock_get_user, authenticated_info, district
    ):
        from server.campaigns.gql_types import DistrictFilter

        mock_get_user.return_value = authenticated_info.context.request.user
        query = CampaignQuery()
        result = query.districts(
            authenticated_info, filters=DistrictFilter()
        )
        assert len(result) >= 1
