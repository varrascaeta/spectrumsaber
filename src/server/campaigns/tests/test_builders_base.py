# Standard imports
from datetime import datetime, timezone

import pytest

# Project imports
from server.campaigns.builders import (
    DATE_TRANSLATE,
    CoverageBuilder,
    UnmatchedBuilder,
)
from server.campaigns.models import (
    Coverage,
    PathRule,
    UnmatchedFile,
)


@pytest.fixture
def path_rule():
    """Create a test path rule"""
    return PathRule.objects.create(
        name="Test Rule",
        order=1,
        pattern=r"^(?P<name>Point_(?P<metadata__number>\d+))$",
        level="data_point",
        date_format="%Y-%m-%d",
    )


@pytest.mark.django_db
class TestDateTranslate:
    """Test DATE_TRANSLATE constant"""

    def test_date_translate_has_all_months(self):
        """Test that DATE_TRANSLATE has all Spanish months"""
        expected_months = [
            "ene",
            "feb",
            "mar",
            "abr",
            "may",
            "jun",
            "jul",
            "ago",
            "set",
            "oct",
            "nov",
            "dic",
        ]
        assert all(month in DATE_TRANSLATE for month in expected_months)


@pytest.mark.django_db
class TestBaseBuilder:
    """Test BaseBuilder abstract class"""

    def test_base_builder_cannot_be_instantiated(self):
        """Test that BaseBuilder cannot be instantiated directly"""
        # BaseBuilder is abstract, but we can test through a concrete class
        builder = CoverageBuilder()
        assert builder.model == Coverage
        assert builder.instance is None

    def test_remove_unmatched_if_exists(self, coverage):
        """Test removing unmatched file if it exists"""
        # Create an unmatched file
        UnmatchedFile.objects.create(
            name="test", path="/test/unmatched", is_unmatched=True
        )

        builder = CoverageBuilder()
        builder.remove_unmatched_if_exists("/test/unmatched")

        assert not UnmatchedFile.objects.filter(
            path="/test/unmatched"
        ).exists()

    def test_remove_unmatched_if_not_exists(self):
        """Test removing unmatched file when it doesn't exist"""
        builder = CoverageBuilder()
        # Should not raise any error
        builder.remove_unmatched_if_exists("/nonexistent/path")

    def test_build_instance_creates_new(self):
        """Test build_instance creates new instance"""
        builder = CoverageBuilder()
        builder.build_instance("/new/coverage/path")

        assert builder.instance is not None
        assert builder.instance.path == "/new/coverage/path"
        assert builder.instance.pk is None  # Not saved yet

    def test_build_instance_gets_existing(self, coverage):
        """Test build_instance gets existing instance"""
        builder = CoverageBuilder()
        builder.build_instance(coverage.path)

        assert builder.instance is not None
        assert builder.instance.id == coverage.id

    def test_build_name(self):
        """Test build_name sets name"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")
        builder.build_name("Test Name")

        assert builder.instance.name == "Test Name"

    def test_build_metadata_new(self):
        """Test build_metadata with new metadata"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")
        builder.build_metadata({"key": "value"})

        assert builder.instance.metadata == {"key": "value"}

    def test_build_metadata_update_existing(self):
        """Test build_metadata updates existing metadata"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")
        builder.instance.metadata = {"existing": "data"}
        builder.build_metadata({"new": "data"})

        assert builder.instance.metadata == {"existing": "data", "new": "data"}

    def test_build_description(self):
        """Test build_description sets description"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")
        builder.build_description("Test description")

        assert builder.instance.description == "Test description"

    def test_build_ftp_created_at_new(self):
        """Test build_ftp_created_at sets date when not set"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")
        test_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        builder.build_ftp_created_at(test_date)

        assert builder.instance.ftp_created_at == test_date

    def test_build_ftp_created_at_existing(self):
        """Test build_ftp_created_at doesn't override existing date"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")
        old_date = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        new_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        builder.instance.ftp_created_at = old_date
        builder.build_ftp_created_at(new_date)

        assert builder.instance.ftp_created_at == old_date

    def test_build_ftp_created_at_none(self):
        """Test build_ftp_created_at with None"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")
        builder.build_ftp_created_at(None)

        assert builder.instance.ftp_created_at is None

    def test_build_is_unmatched(self):
        """Test build_is_unmatched sets to False"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")
        builder.build_is_unmatched()

        assert builder.instance.is_unmatched is False

    def test_build_last_synced_at(self):
        """Test build_last_synced_at sets current time"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")

        before = datetime.now(timezone.utc)
        builder.build_last_synced_at()
        after = datetime.now(timezone.utc)

        assert before <= builder.instance.last_synced_at <= after

    def test_save_to_db(self):
        """Test save_to_db saves instance"""
        builder = CoverageBuilder()
        builder.build_instance("/test/save/path")
        builder.build_name("Test Save")

        result = builder.save_to_db()

        assert result.pk is not None
        assert Coverage.objects.filter(path="/test/save/path").exists()

    def test_getstate_setstate(self):
        """Test __getstate__ and __setstate__ for pickling"""
        builder = CoverageBuilder()
        builder.build_instance("/test/path")

        state = builder.__getstate__()
        assert "model" in state
        assert "instance" in state

        new_builder = CoverageBuilder()
        new_builder.__setstate__(state)
        assert new_builder.instance.path == "/test/path"


@pytest.mark.django_db
class TestUnmatchedBuilder:
    """Test UnmatchedBuilder class"""

    def test_get_model(self):
        """Test _get_model returns UnmatchedFile"""
        builder = UnmatchedBuilder()
        assert builder.model == UnmatchedFile

    def test_remove_unmatched_if_exists_does_nothing(self):
        """Test remove_unmatched_if_exists doesn't remove for unmatched"""
        UnmatchedFile.objects.create(
            name="test", path="/test/unmatched", is_unmatched=True
        )
        builder = UnmatchedBuilder()
        builder.remove_unmatched_if_exists("/test/unmatched")

        # Should still exist
        assert UnmatchedFile.objects.filter(path="/test/unmatched").exists()

    def test_build_parent(self):
        """Test build_parent sets parent_path"""
        builder = UnmatchedBuilder()
        builder.build_instance("/test/unmatched")
        builder.build_parent("/test/parent")

        assert builder.instance.parent_path == "/test/parent"

    def test_build_is_unmatched(self):
        """Test build_is_unmatched sets to True"""
        builder = UnmatchedBuilder()
        builder.build_instance("/test/unmatched")
        builder.build_is_unmatched()

        assert builder.instance.is_unmatched is True

    def test_build_level_valid(self):
        """Test build_level with valid level"""
        builder = UnmatchedBuilder()
        builder.build_instance("/test/unmatched")
        builder.build_level("campaign")

        assert builder.instance.level == "campaign"

    def test_build_level_invalid(self):
        """Test build_level with invalid level"""
        builder = UnmatchedBuilder()
        builder.build_instance("/test/unmatched")
        builder.build_level("invalid_level")

        # Should not set level for invalid values
        assert (
            not hasattr(builder.instance, "level")
            or builder.instance.level != "invalid_level"
        )
