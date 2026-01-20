# Standard imports
import pytest
from datetime import datetime

# Django imports
from django.db.models.signals import post_save

# Project imports
from src.campaigns.models import (
    Campaign,
    Coverage,
    PathRule,
    UnmatchedFile,
)
from src.campaigns.signals import match_new_patterns
from src.places.models import Country, District, Province


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
        name="123-20250115-COR",
        path="/test/coverage/123-20250115-COR",
        coverage=coverage,
        district=district,
        date=datetime(2025, 1, 15),
        external_id="123",
        metadata={"geo_code": "COR"},
    )


@pytest.fixture
def disconnect_signals():
    """Fixture to temporarily disconnect signals during setup"""
    post_save.disconnect(match_new_patterns, sender=PathRule)
    yield
    post_save.connect(match_new_patterns, sender=PathRule)


@pytest.fixture
def unmatched_campaign():
    return UnmatchedFile.objects.create(  # noqa: F841
        name="123-20250115-COR",
        path="/test/coverage/123-20250115-COR",
        parent_path="/test/coverage",
        level="campaign",
        is_unmatched=True,
    )


@pytest.fixture
def unmatched_datapoint():
    return UnmatchedFile.objects.create(  # noqa: F841
        name="Punto 01",
        path="/test/coverage/123-20250115-COR/Punto_01",
        parent_path="/test/coverage/123-20250115-COR",
        level="data_point",
        is_unmatched=True,
    )


@pytest.fixture
def campaign_rule_dict():
    """Create a PathRule for campaigns"""
    return {
        "name": "Campaign ID-YYYYMMDD-GEO",
        "order": 1,
        "pattern": "^(?P<external_id>\\d+)-(?P<date>\\d{8})-(?P<metadata__geo_code>.+)$",  # noqa: E501
        "date_format": None,
        "level": "campaign",
    }


@pytest.fixture
def datapoint_rule_dict():
    """Create a PathRule for data points"""
    return {
        "name": "Data Point Punto NN",
        "order": 1,
        "pattern": "^Punto (?P<order>\\d+)$",
        "date_format": None,
        "level": "data_point",
    }


@pytest.mark.django_db
class TestMatchNewPatternsSignal:
    """Test match_new_patterns signal"""

    def test_signal_matches_unmatched_campaign_files(
        self,
        coverage,
        disconnect_signals,
        unmatched_campaign,
        campaign_rule_dict,
    ):
        """Test signal matches unmatched campaign files when rule created"""
        # Reconnect signal
        post_save.connect(match_new_patterns, sender=PathRule)

        # Create PathRule that matches the pattern
        PathRule.objects.create(**campaign_rule_dict)

        # Verify unmatched file was deleted (matched and converted)
        assert not UnmatchedFile.objects.filter(
            id=unmatched_campaign.id
        ).exists()

    def test_signal_matches_unmatched_datapoint_files(
        self,
        campaign,
        disconnect_signals,
        unmatched_datapoint,
        datapoint_rule_dict,
    ):
        """Test signal matches unmatched data point files"""
        # Reconnect signal
        post_save.connect(match_new_patterns, sender=PathRule)

        # Create PathRule for data points
        PathRule.objects.create(**datapoint_rule_dict)

        # Verify unmatched file was deleted
        assert not UnmatchedFile.objects.filter(
            id=unmatched_datapoint.id
        ).exists()

    def test_signal_does_not_match_different_level(
        self,
        disconnect_signals,
        coverage,
        unmatched_campaign,
        unmatched_datapoint,
        campaign_rule_dict,
    ):
        """Test signal only matches files of same level as rule"""
        # Create rule for campaign level only
        PathRule.objects.create(**campaign_rule_dict)

        # Verify only campaign level file was processed
        # (may or may not be deleted depending on match_pattern result)
        # but data_point level file should remain
        assert UnmatchedFile.objects.filter(id=unmatched_datapoint.id).exists()

    def test_signal_does_not_fire_on_rule_update(
        self,
        coverage,
        disconnect_signals,
        unmatched_campaign,
        campaign_rule_dict,
    ):
        """Test signal does not fire when rule is updated"""
        # Create rule without signal
        rule = PathRule.objects.create(**campaign_rule_dict)

        # Reconnect signal
        post_save.connect(match_new_patterns, sender=PathRule)

        # Update rule (should not trigger signal)
        PathRule.objects.filter(id=rule.id).update(name="Updated Rule")

        # Unmatched file should still exist since signal only fires on create
        assert UnmatchedFile.objects.filter(id=unmatched_campaign.id).exists()

    def test_signal_handles_multiple_unmatched_files(
        self, coverage, disconnect_signals, campaign_rule_dict
    ):
        """Test signal processes multiple unmatched files"""
        # Create multiple unmatched files
        for campaign_name in [
            "123-20250115-COR",
            "456-20250220-SFE",
            "789-20250325-BUE",
        ]:
            UnmatchedFile.objects.create(
                name=campaign_name,
                path=f"/test/coverage/{campaign_name}",
                parent_path="/test/coverage",
                level="campaign",
                is_unmatched=True,
            )

        # Reconnect signal
        post_save.connect(match_new_patterns, sender=PathRule)
        PathRule.objects.create(**campaign_rule_dict)

        # All matching files should be processed
        # (may be deleted if successfully matched)
        initial_count = UnmatchedFile.objects.filter(level="campaign").count()
        assert initial_count == 0
        assert Campaign.objects.count() == 3

    def test_signal_handles_pattern_without_match(
        self, disconnect_signals, campaign_rule_dict
    ):
        """Test signal handles unmatched patterns gracefully"""
        # Create unmatched file that won't match pattern
        unmatched = UnmatchedFile.objects.create(  # noqa: F841
            name="NoMatch_File",
            path="/test/coverage/NoMatch_File",
            parent_path="/test/coverage",
            level="campaign",
            is_unmatched=True,
        )

        # Reconnect signal
        post_save.connect(match_new_patterns, sender=PathRule)

        # Create rule with different pattern
        PathRule.objects.create(**campaign_rule_dict)
        # Unmatched file should still exist (no match)
        assert UnmatchedFile.objects.filter(id=unmatched.id).exists()
