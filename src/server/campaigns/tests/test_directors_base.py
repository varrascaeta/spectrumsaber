# Standard imports
from datetime import datetime, timezone

import pytest

# Project imports
from server.campaigns.directors import (
    BaseDirector,
    CampaignDirector,
    CoverageDirector,
    UnmatchedDirector,
)
from server.campaigns.models import (
    Campaign,
    Coverage,
    PathRule,
    UnmatchedFile,
)


@pytest.fixture
def campaign_rule():
    """Create a test campaign rule"""
    return PathRule.objects.create(
        name="Test Rule",
        order=1,
        pattern=r"^(?P<external_id>_(?P<metadata__number>\d+))$",
        level="campaign",
        date_format="%Y-%m-%d",
    )


@pytest.mark.django_db
class TestBaseDirector:
    """Test BaseDirector abstract class"""

    def test_base_director_cannot_be_instantiated(self):
        """Test that BaseDirector cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BaseDirector()

    def test_base_director_has_builder(self):
        """Test that concrete directors have a builder"""
        director = CoverageDirector()
        assert director._builder is not None

    def test_construct_builds_base_attributes(self):
        """Test that construct builds all base file attributes"""
        director = CoverageDirector()
        file_data = {
            "path": "/test/new_coverage",
            "name": "New Coverage",
            "metadata": {"key": "value"},
            "description": "Test description",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "parent": "",
        }

        director.construct(file_data)

        assert director._builder.instance.path == "/test/new_coverage"
        assert director._builder.instance.name == "New Coverage"
        assert director._builder.instance.metadata == {"key": "value"}
        assert director._builder.instance.description == "Test description"
        assert director._builder.instance.is_unmatched is False
        assert director._builder.instance.last_synced_at is not None

    def test_commit_saves_instance(self):
        """Test that commit saves the instance to database"""
        director = CoverageDirector()
        file_data = {
            "path": "/test/commit_coverage",
            "name": "Commit Coverage",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.id is not None
        assert Coverage.objects.filter(path="/test/commit_coverage").exists()


@pytest.mark.django_db
class TestUnmatchedDirector:
    """Test UnmatchedDirector class"""

    def test_get_builder_returns_unmatched_builder(self):
        """Test that _get_builder returns UnmatchedBuilder"""
        director = UnmatchedDirector()
        from server.campaigns.builders import UnmatchedBuilder

        assert isinstance(director._builder, UnmatchedBuilder)

    def test_construct_unmatched_file(self):
        """Test constructing an unmatched file"""
        director = UnmatchedDirector()
        file_data = {
            "path": "/test/unmatched/file.txt",
            "name": "file.txt",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "parent": "/test/unmatched",
            "level": "measurement",
        }

        director.construct(file_data)

        assert director._builder.instance.path == "/test/unmatched/file.txt"
        assert director._builder.instance.name == "file.txt"
        assert director._builder.instance.is_unmatched is True
        assert director._builder.instance.level == "measurement"

    def test_construct_and_commit_unmatched(self):
        """Test full construct and commit flow for unmatched file"""
        director = UnmatchedDirector()
        file_data = {
            "path": "/test/unmatched2/file.txt",
            "name": "file.txt",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "parent": "/test/unmatched2",
            "level": "campaign",
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.id is not None
        assert UnmatchedFile.objects.filter(
            path="/test/unmatched2/file.txt"
        ).exists()

    def test_construct_unmatched_with_invalid_level(self):
        """Test constructing unmatched file with invalid level"""
        director = UnmatchedDirector()
        file_data = {
            "path": "/test/unmatched3/file.txt",
            "name": "file.txt",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "parent": "/test/unmatched3",
            "level": "invalid_level",
        }

        director.construct(file_data)

        assert director._builder.instance.level == ""


@pytest.mark.django_db
class TestCoverageDirector:
    """Test CoverageDirector class"""

    def test_get_builder_returns_coverage_builder(self):
        """Test that _get_builder returns CoverageBuilder"""
        director = CoverageDirector()
        from server.campaigns.builders import CoverageBuilder

        assert isinstance(director._builder, CoverageBuilder)

    def test_construct_coverage(self):
        """Test constructing a coverage"""
        director = CoverageDirector()
        file_data = {
            "path": "/test/new_coverage",
            "name": "New Coverage",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)

        assert director._builder.instance.path == "/test/new_coverage"
        assert director._builder.instance.name == "New Coverage"

    def test_construct_and_commit_coverage(self):
        """Test full construct and commit flow for coverage"""
        director = CoverageDirector()
        file_data = {
            "path": "/test/coverage_full",
            "name": "Coverage Full",
            "metadata": {"year": "2025"},
            "description": "Full test coverage",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.id is not None
        saved = Coverage.objects.get(path="/test/coverage_full")
        assert saved.name == "Coverage Full"
        assert saved.metadata == {"year": "2025"}
        assert saved.description == "Full test coverage"

    def test_construct_coverage_updates_existing(self, coverage):
        """Test that constructing existing coverage updates it"""
        director = CoverageDirector()
        file_data = {
            "path": "/test/coverage",
            "name": "Updated Coverage",
            "metadata": {"updated": True},
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.id == coverage.id
        assert instance.name == "Updated Coverage"
        assert instance.metadata == {"updated": True}


@pytest.mark.django_db
class TestCampaignDirector:
    """Test CampaignDirector class"""

    def test_get_builder_returns_campaign_builder(self):
        """Test that _get_builder returns CampaignBuilder"""
        director = CampaignDirector()
        from server.campaigns.builders import CampaignBuilder

        assert isinstance(director._builder, CampaignBuilder)

    def test_construct_campaign(self, coverage, district, campaign_rule):
        """Test constructing a campaign"""
        director = CampaignDirector()
        file_data = {
            "path": "/test/coverage/456-20251001-Campaign",
            "name": "456-20251001-Campaign",
            "parent": "/test/coverage",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "date": "2025-10-01",
            "external_id": "456",
            "rule_id": campaign_rule.id,
        }

        director.construct(file_data)

        assert (
            director._builder.instance.path
            == "/test/coverage/456-20251001-Campaign"
        )
        assert director._builder.instance.name == "456-20251001-Campaign"
        assert director._builder.instance.external_id == "456"

    def test_construct_and_commit_campaign(self, coverage, district):
        """Test full construct and commit flow for campaign"""
        director = CampaignDirector()
        file_data = {
            "path": "/test/coverage/campaign_full",
            "name": "Campaign Full",
            "parent": "/test/coverage",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "date": "2025-01-15",
            "external_id": "EXT789",
            "metadata": {"geo_code": "TEST001"},
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.id is not None
        saved = Campaign.objects.get(path="/test/coverage/campaign_full")
        assert saved.name == "Campaign Full"
        assert saved.external_id == "EXT789"
        assert saved.coverage_id == coverage.id
        assert saved.district_id == district.id

    def test_construct_campaign_without_district(self, coverage):
        """Test constructing campaign without district metadata"""
        director = CampaignDirector()
        file_data = {
            "path": "/test/coverage/campaign_no_district",
            "name": "Campaign No District",
            "parent": "/test/coverage",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "date": "2025-01-15",
            "external_id": "EXT111",
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.district_id is None
