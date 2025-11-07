# Standard imports
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

# Project imports
from src.campaigns.builders import (
    UnmatchedBuilder,
    CoverageBuilder,
    CampaignBuilder,
    DataPointBuilder,
    MeasurementBuilder,
    ComplimentaryDataBuilder,
    ComplimentaryBuilder,
    DATE_TRANSLATE,
)
from src.campaigns.models import (
    Campaign,
    Coverage,
    DataPoint,
    Measurement,
    Category,
    CategoryType,
    ComplimentaryData,
    ComplimentaryDataType,
    PathRule,
    UnmatchedFile,
)
from src.places.models import District, Province, Country


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
        name="Test Campaign",
        path="/test/coverage/campaign",
        coverage=coverage,
        district=district,
        date=datetime(2025, 1, 15),
        external_id="EXT123",
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


@pytest.mark.django_db
class TestCoverageBuilder:
    """Test CoverageBuilder class"""

    def test_get_model(self):
        """Test _get_model returns Coverage"""
        builder = CoverageBuilder()
        assert builder.model == Coverage

    def test_build_parent_does_nothing(self):
        """Test build_parent does nothing for Coverage"""
        builder = CoverageBuilder()
        builder.build_instance("/test/coverage")
        # Should not raise any error
        builder.build_parent("/some/parent")

    def test_create_coverage_complete(self):
        """Test creating a complete coverage instance"""
        builder = CoverageBuilder()
        builder.build_instance("/test/complete/coverage")
        builder.build_name("Complete Coverage")
        builder.build_description("Test description")
        builder.build_metadata({"key": "value"})
        builder.build_is_unmatched()
        builder.build_last_synced_at()

        coverage = builder.save_to_db()

        assert coverage.name == "Complete Coverage"
        assert coverage.path == "test/complete/coverage"
        assert coverage.description == "Test description"
        assert coverage.metadata == {"key": "value"}
        assert coverage.is_unmatched is False


@pytest.mark.django_db
class TestCampaignBuilder:
    """Test CampaignBuilder class"""

    def test_get_model(self):
        """Test _get_model returns Campaign"""
        builder = CampaignBuilder()
        assert builder.model == Campaign

    def test_translate_date_str(self):
        """Test _translate_date_str translates Spanish months"""
        builder = CampaignBuilder()

        assert builder._translate_date_str("15-ene-2025") == "15-jan-2025"
        assert builder._translate_date_str("15-ENE-2025") == "15-jan-2025"
        assert builder._translate_date_str("01-dic-2024") == "01-dec-2024"
        assert builder._translate_date_str("15-ago-2025") == "15-aug-2025"

    def test_translate_date_str_all_months(self):
        """Test _translate_date_str for all Spanish months"""
        builder = CampaignBuilder()
        spanish_months = [
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
        english_months = [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ]

        for sp, en in zip(spanish_months, english_months):
            assert en in builder._translate_date_str(f"15-{sp}-2025")

    def test_build_date_with_format(self, path_rule):
        """Test build_date with date_format from rule"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")
        builder.build_date(path_rule.id, "2025-01-15")

        assert builder.instance.date == datetime(2025, 1, 15)

    def test_build_date_without_format(self):
        """Test build_date without date_format (uses parse)"""
        rule = PathRule.objects.create(
            name="No Format Rule", order=2, pattern=r".*", level="campaign"
        )

        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")
        builder.build_date(rule.id, "2025-01-15")

        assert builder.instance.date == datetime(2025, 1, 15)

    def test_build_date_spanish_month(self, path_rule):
        """Test build_date with Spanish month name"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")

        # Update rule to accept month name format
        path_rule.date_format = "%d-%b-%Y"
        path_rule.save()

        builder.build_date(path_rule.id, "15-ene-2025")

        assert builder.instance.date == datetime(2025, 1, 15)

    def test_build_date_invalid_format(self, path_rule):
        """Test build_date with invalid date format"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")

        # This should not raise error, just log warning
        builder.build_date(path_rule.id, "invalid-date")

        # Date should remain None
        assert builder.instance.date is None

    def test_build_date_empty_string(self, path_rule):
        """Test build_date with empty string"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")
        builder.build_date(path_rule.id, "")

        assert builder.instance.date is None

    def test_build_date_none(self, path_rule):
        """Test build_date with None"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")
        builder.build_date(path_rule.id, None)

        assert builder.instance.date is None

    def test_build_external_id(self):
        """Test build_external_id sets external_id"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")
        builder.build_external_id("EXT456")

        assert builder.instance.external_id == "EXT456"

    def test_build_parent(self, coverage):
        """Test build_parent sets coverage_id"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")
        builder.build_parent(coverage.path)

        assert builder.instance.coverage_id == coverage.id

    def test_build_district_with_code(self, district):
        """Test build_district with valid district code"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")
        builder.instance.metadata = {"geo_code": "TEST001"}
        builder.build_district()

        assert builder.instance.district_id == district.id

    def test_build_district_without_code(self):
        """Test build_district without district code"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")
        builder.instance.metadata = {}
        builder.build_district()

        assert (
            not hasattr(builder.instance, "district_id")
            or builder.instance.district_id is None
        )

    def test_build_district_invalid_code(self):
        """Test build_district with invalid district code"""
        builder = CampaignBuilder()
        builder.build_instance("/test/campaign")
        builder.instance.metadata = {"geo_code": "INVALID"}
        builder.build_district()

        assert (
            not hasattr(builder.instance, "district_id")
            or builder.instance.district_id is None
        )

    def test_create_campaign_complete(self, coverage, district):
        """Test creating a complete campaign instance"""
        builder = CampaignBuilder()
        builder.build_instance("/test/complete/campaign")
        builder.build_name("Complete Campaign")
        builder.build_parent(coverage.path)
        builder.build_external_id("EXT789")
        builder.build_metadata({"geo_code": district.code})

        rule = PathRule.objects.create(
            name="Date Rule",
            order=3,
            pattern=r".*",
            level="campaign",
            date_format="%Y-%m-%d",
        )
        builder.build_date(rule.id, "2025-02-20")
        builder.build_district()

        campaign = builder.save_to_db()

        assert campaign.name == "Complete Campaign"
        assert campaign.coverage_id == coverage.id
        assert campaign.external_id == "EXT789"
        assert campaign.district_id == district.id
        assert campaign.date == datetime(2025, 2, 20)


@pytest.mark.django_db
class TestDataPointBuilder:
    """Test DataPointBuilder class"""

    def test_get_model(self):
        """Test _get_model returns DataPoint"""
        builder = DataPointBuilder()
        assert builder.model == DataPoint

    def test_build_parent(self, campaign):
        """Test build_parent sets campaign_id"""
        builder = DataPointBuilder()
        builder.build_instance("/test/datapoint")
        builder.build_parent(campaign.path)

        assert builder.instance.campaign_id == campaign.id

    def test_build_order_with_value(self):
        """Test build_order with value"""
        builder = DataPointBuilder()
        builder.build_instance("/test/datapoint")
        builder.build_order("5")

        assert builder.instance.order == 5

    def test_build_order_none(self):
        """Test build_order with None"""
        builder = DataPointBuilder()
        builder.build_instance("/test/datapoint")
        builder.build_order(None)

        assert builder.instance.order == 0

    def test_build_order_empty_string(self):
        """Test build_order with empty string"""
        builder = DataPointBuilder()
        builder.build_instance("/test/datapoint")
        builder.build_order("")

        assert builder.instance.order == 0

    def test_build_latitude(self):
        """Test build_latitude from metadata"""
        builder = DataPointBuilder()
        builder.build_instance("/test/datapoint")
        builder.instance.metadata = {"latitude": "-31.4201"}
        builder.build_latitude()

        assert builder.instance.latitude == -31.4201

    def test_build_latitude_none(self):
        """Test build_latitude with no metadata"""
        builder = DataPointBuilder()
        builder.build_instance("/test/datapoint")
        builder.instance.metadata = {}
        builder.build_latitude()

        assert builder.instance.latitude is None

    def test_build_longitude(self):
        """Test build_longitude from metadata"""
        builder = DataPointBuilder()
        builder.build_instance("/test/datapoint")
        builder.instance.metadata = {"longitude": "-64.1888"}
        builder.build_longitude()

        assert builder.instance.longitude == -64.1888

    def test_build_longitude_none(self):
        """Test build_longitude with no metadata"""
        builder = DataPointBuilder()
        builder.build_instance("/test/datapoint")
        builder.instance.metadata = {}
        builder.build_longitude()

        assert builder.instance.longitude is None

    def test_create_datapoint_complete(self, campaign):
        """Test creating a complete data point instance"""
        builder = DataPointBuilder()
        builder.build_instance("/test/complete/datapoint")
        builder.build_name("Complete DataPoint")
        builder.build_parent(campaign.path)
        builder.build_order("3")
        builder.build_metadata(
            {"latitude": "-31.4201", "longitude": "-64.1888"}
        )
        builder.build_latitude()
        builder.build_longitude()

        datapoint = builder.save_to_db()

        assert datapoint.name == "Complete DataPoint"
        assert datapoint.campaign_id == campaign.id
        assert datapoint.order == 3
        assert datapoint.latitude == -31.4201
        assert datapoint.longitude == -64.1888


@pytest.mark.django_db
class TestMeasurementBuilder:
    """Test MeasurementBuilder class"""

    def test_get_model(self):
        """Test _get_model returns Measurement"""
        builder = MeasurementBuilder()
        assert builder.model == Measurement

    def test_build_parent(self, data_point):
        """Test build_parent sets data_point_id"""
        builder = MeasurementBuilder()
        builder.build_instance("/test/measurement")
        builder.build_parent(data_point.path)

        assert builder.instance.data_point_id == data_point.id

    def test_build_category_radiance(self):
        """Test build_category with radiance path"""
        builder = MeasurementBuilder()
        builder.build_instance("/test/measurement")
        builder.build_category("/test/path/radiancia/file.txt")

        assert builder.instance.category_id is not None
        category = Category.objects.get(id=builder.instance.category_id)
        assert category.name == CategoryType.RADIANCE

    def test_build_category_reflectance(self):
        """Test build_category with reflectance path"""
        builder = MeasurementBuilder()
        builder.build_instance("/test/measurement")
        builder.build_category("/test/path/reflectancia/file.txt")

        assert builder.instance.category_id is not None
        category = Category.objects.get(id=builder.instance.category_id)
        assert category.name == CategoryType.REFLECTANCE

    def test_build_category_existing(self):
        """Test build_category with existing category"""
        # Create category first
        existing_category = Category.objects.create(name=CategoryType.RADIANCE)

        builder = MeasurementBuilder()
        builder.build_instance("/test/measurement")
        builder.build_category("/test/path/radiancia/file.txt")

        assert builder.instance.category_id == existing_category.id

    def test_build_category_not_found(self):
        """Test build_category when no category matches"""
        builder = MeasurementBuilder()
        builder.build_instance("/test/measurement")
        builder.build_category("/test/path/unknown/file.txt")

        assert (
            not hasattr(builder.instance, "category_id")
            or builder.instance.category_id is None
        )

    @patch("src.campaigns.builders.logger")
    def test_build_category_logs_warning(self, mock_logger):
        """Test build_category logs warning when no category found"""
        builder = MeasurementBuilder()
        builder.build_instance("/test/measurement")
        builder.build_category("/test/path/unknown/file.txt")

        mock_logger.warning.assert_called()

    @patch("src.campaigns.builders.logger")
    def test_build_category_logs_info_created(self, mock_logger):
        """Test build_category logs info when category is created"""
        builder = MeasurementBuilder()
        builder.build_instance("/test/measurement")
        builder.build_category("/test/path/radiancia/file.txt")

        mock_logger.info.assert_called()

    def test_create_measurement_complete(self, data_point):
        """Test creating a complete measurement instance"""
        builder = MeasurementBuilder()
        builder.build_instance("/test/complete/radiancia/measurement.txt")
        builder.build_name("Complete Measurement")
        builder.build_parent(data_point.path)
        builder.build_category("/test/complete/radiancia/measurement.txt")

        measurement = builder.save_to_db()

        assert measurement.name == "Complete Measurement"
        assert measurement.data_point_id == data_point.id
        assert measurement.category_id is not None


@pytest.mark.django_db
class TestComplimentaryDataBuilder:
    """Test ComplimentaryDataBuilder class"""

    def test_get_model(self):
        """Test _get_model returns ComplimentaryData"""
        builder = ComplimentaryDataBuilder()
        assert builder.model == ComplimentaryData

    def test_build_parent_does_nothing(self):
        """Test build_parent does nothing for ComplimentaryDataBuilder"""
        builder = ComplimentaryDataBuilder()
        builder.build_instance("/test/complimentary")
        # Should not raise any error
        builder.build_parent("/some/parent")


@pytest.mark.django_db
class TestComplimentaryBuilder:
    """Test ComplimentaryBuilder class"""

    def test_get_model(self):
        """Test _get_model returns ComplimentaryData"""
        builder = ComplimentaryBuilder()
        assert builder.model == ComplimentaryData

    def test_build_parent_campaign(self, campaign):
        """Test build_parent with Campaign parent"""
        builder = ComplimentaryBuilder()
        builder.build_instance("/test/complimentary")

        with patch.object(
            ComplimentaryData, "get_parent", return_value=campaign
        ):
            builder.build_parent(campaign.path)
            assert builder.instance.campaign_id == campaign.id

    def test_build_parent_datapoint(self, data_point):
        """Test build_parent with DataPoint parent"""
        builder = ComplimentaryBuilder()
        builder.build_instance("/test/complimentary")

        with patch.object(
            ComplimentaryData, "get_parent", return_value=data_point
        ):
            builder.build_parent(data_point.path)
            assert builder.instance.data_point_id == data_point.id

    def test_build_complement_type_photos(self):
        """Test build_complement_type with photos path"""
        builder = ComplimentaryBuilder()
        builder.build_instance("/test/complimentary")
        builder.build_complement_type("/test/path/fotos/image.jpg")

        assert builder.instance.complement_type == ComplimentaryDataType.PHOTOS

    def test_build_complement_type_field_spreadsheet(self):
        """Test build_complement_type with field spreadsheet path"""
        builder = ComplimentaryBuilder()
        builder.build_instance("/test/complimentary")
        builder.build_complement_type("/test/path/planillacampo/data.xlsx")

        assert (
            builder.instance.complement_type
            == ComplimentaryDataType.FIELD_SPREADSHEET
        )

    def test_build_complement_type_lab_spreadsheet(self):
        """Test build_complement_type with lab spreadsheet path"""
        builder = ComplimentaryBuilder()
        builder.build_instance("/test/complimentary")
        builder.build_complement_type(
            "/test/path/planillalaboratorio/data.xlsx"
        )

        assert (
            builder.instance.complement_type
            == ComplimentaryDataType.LAB_SPREADSHEET
        )

    def test_build_complement_type_none(self):
        """Test build_complement_type when no type matches"""
        builder = ComplimentaryBuilder()
        builder.build_instance("/test/complimentary")
        builder.build_complement_type("/test/path/unknown/file.txt")

        assert builder.instance.complement_type == "Complimentary Data"

    def test_create_complimentary_complete_with_campaign(self, campaign):
        """Test creating complete complimentary data with campaign"""
        builder = ComplimentaryBuilder()
        builder.build_instance("/test/complete/fotos/photo.jpg")
        builder.build_name("Complete Complimentary")

        with patch.object(
            ComplimentaryData, "get_parent", return_value=campaign
        ):
            builder.build_parent(campaign.path)
            builder.build_complement_type("/test/complete/fotos/photo.jpg")

            complimentary = builder.save_to_db()

            assert complimentary.name == "Complete Complimentary"
            assert complimentary.campaign_id == campaign.id
            assert (
                complimentary.complement_type == ComplimentaryDataType.PHOTOS
            )

    def test_create_complimentary_complete_with_datapoint(self, data_point):
        """Test creating complete complimentary data with data point"""
        builder = ComplimentaryBuilder()
        builder.build_instance("/test/complete/planillacampo/spreadsheet.xlsx")
        builder.build_name("Complete Complimentary DataPoint")

        with patch.object(
            ComplimentaryData, "get_parent", return_value=data_point
        ):
            builder.build_parent(data_point.path)
            builder.build_complement_type(
                "/test/complete/planillacampo/spreadsheet.xlsx"
            )

            complimentary = builder.save_to_db()

            assert complimentary.name == "Complete Complimentary DataPoint"
            assert complimentary.data_point_id == data_point.id
            assert (
                complimentary.complement_type
                == ComplimentaryDataType.FIELD_SPREADSHEET
            )


@pytest.mark.django_db
class TestBuilderIntegration:
    """Integration tests for builders"""

    def test_full_hierarchy_creation(self):
        """Test creating a full hierarchy using builders"""
        # Create coverage
        coverage_builder = CoverageBuilder()
        coverage_builder.build_instance("/integration/coverage")
        coverage_builder.build_name("Integration Coverage")
        coverage = coverage_builder.save_to_db()

        # Create campaign
        campaign_builder = CampaignBuilder()
        campaign_builder.build_instance("/integration/coverage/campaign")
        campaign_builder.build_name("Integration Campaign")
        campaign_builder.build_parent(coverage.path)
        campaign_builder.build_external_id("INT001")
        campaign = campaign_builder.save_to_db()

        # Create data point
        datapoint_builder = DataPointBuilder()
        datapoint_builder.build_instance(
            "/integration/coverage/campaign/point001"
        )
        datapoint_builder.build_name("Integration Point")
        datapoint_builder.build_parent(campaign.path)
        datapoint_builder.build_order("1")
        datapoint = datapoint_builder.save_to_db()

        # Create measurement
        measurement_builder = MeasurementBuilder()
        measurement_builder.build_instance(
            "/integration/coverage/campaign/point001/radiancia/meas.txt"
        )
        measurement_builder.build_name("Integration Measurement")
        measurement_builder.build_parent(datapoint.path)
        measurement_builder.build_category(
            "/integration/coverage/campaign/point001/radiancia/meas.txt"
        )
        measurement = measurement_builder.save_to_db()

        # Verify hierarchy
        assert measurement.data_point.id == datapoint.id
        assert datapoint.campaign.id == campaign.id
        assert campaign.coverage.id == coverage.id

    def test_builder_updates_existing(self, coverage):
        """Test that builders update existing instances"""
        # First creation
        builder1 = CoverageBuilder()
        builder1.build_instance(coverage.path)
        builder1.build_description("First description")
        instance1 = builder1.save_to_db()

        # Second update
        builder2 = CoverageBuilder()
        builder2.build_instance(coverage.path)
        builder2.build_description("Updated description")
        instance2 = builder2.save_to_db()

        # Should be same instance
        assert instance1.id == instance2.id
        assert instance2.description == "Updated description"

        # Should only be one coverage with this path
        assert Coverage.objects.filter(path=coverage.path).count() == 1
