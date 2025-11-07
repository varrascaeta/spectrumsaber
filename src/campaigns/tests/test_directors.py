# Standard imports
import pytest
from datetime import datetime, timezone

# Project imports
from src.campaigns.directors import (
    BaseDirector,
    UnmatchedDirector,
    CoverageDirector,
    CampaignDirector,
    DataPointDirector,
    MeasurementDirector,
    ComplimentaryDirector,
    get_director_by_class_name,
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
        date=datetime(2025, 1, 15, tzinfo=timezone.utc),
        external_id="EXT123",
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
    return Category.objects.create(name=CategoryType.RADIANCE)


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
        from src.campaigns.builders import UnmatchedBuilder

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
        from src.campaigns.builders import CoverageBuilder

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
        from src.campaigns.builders import CampaignBuilder

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


@pytest.mark.django_db
class TestDataPointDirector:
    """Test DataPointDirector class"""

    def test_get_builder_returns_datapoint_builder(self):
        """Test that _get_builder returns DataPointBuilder"""
        director = DataPointDirector()
        from src.campaigns.builders import DataPointBuilder

        assert isinstance(director._builder, DataPointBuilder)

    def test_construct_datapoint(self, campaign):
        """Test constructing a data point"""
        director = DataPointDirector()
        file_data = {
            "path": "/test/coverage/campaign/point002",
            "name": "Point 002",
            "parent": "/test/coverage/campaign",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "order": "2",
        }

        director.construct(file_data)

        assert director._builder.instance.path == (
            "/test/coverage/campaign/point002"
        )
        assert director._builder.instance.name == "Point 002"
        assert director._builder.instance.order == 2

    def test_construct_and_commit_datapoint(self, campaign):
        """Test full construct and commit flow for data point"""
        director = DataPointDirector()
        file_data = {
            "path": "/test/coverage/campaign/point_full",
            "name": "Point Full",
            "parent": "/test/coverage/campaign",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "order": "5",
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.id is not None
        saved = DataPoint.objects.get(
            path="/test/coverage/campaign/point_full"
        )
        assert saved.name == "Point Full"
        assert saved.campaign_id == campaign.id
        assert saved.order == 5

    def test_construct_datapoint_without_order(self, campaign):
        """Test constructing data point without order"""
        director = DataPointDirector()
        file_data = {
            "path": "/test/coverage/campaign/point_no_order",
            "name": "Point No Order",
            "parent": "/test/coverage/campaign",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.order == 0

    def test_construct_datapoint_with_metadata(self, campaign):
        """Test constructing data point with latitude and longitude"""
        director = DataPointDirector()
        file_data = {
            "path": "/test/coverage/campaign/point_coords",
            "name": "Point Coords",
            "parent": "/test/coverage/campaign",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "order": "3",
            "metadata": {"observacion": "Test observation"},
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.metadata.get("observacion") == "Test observation"


@pytest.mark.django_db
class TestMeasurementDirector:
    """Test MeasurementDirector class"""

    def test_get_builder_returns_measurement_builder(self):
        """Test that _get_builder returns MeasurementBuilder"""
        director = MeasurementDirector()
        from src.campaigns.builders import MeasurementBuilder

        assert isinstance(director._builder, MeasurementBuilder)

    def test_construct_measurement(self, data_point, category):
        """Test constructing a measurement"""
        director = MeasurementDirector()
        file_data = {
            "path": (
                "/test/coverage/campaign/point001/radiancia/"
                "measurement_002.txt"
            ),
            "name": "measurement_002.txt",
            "parent": "/test/coverage/campaign/point001",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)

        assert director._builder.instance.path == (
            "/test/coverage/campaign/point001/radiancia/measurement_002.txt"
        )
        assert director._builder.instance.name == "measurement_002.txt"

    def test_construct_and_commit_measurement(self, data_point, category):
        """Test full construct and commit flow for measurement"""
        director = MeasurementDirector()
        file_data = {
            "path": (
                "/test/coverage/campaign/point001/radiancia/"
                "measurement_full.txt"
            ),
            "name": "measurement_full.txt",
            "parent": "/test/coverage/campaign/point001",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "metadata": {"wavelength": "550nm"},
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.id is not None
        saved = Measurement.objects.get(
            path=(
                "/test/coverage/campaign/point001/radiancia/"
                "measurement_full.txt"
            )
        )
        assert saved.name == "measurement_full.txt"
        assert saved.data_point_id == data_point.id
        assert saved.category_id == category.id
        assert saved.metadata == {"wavelength": "550nm"}

    def test_construct_measurement_reflectance(self, data_point):
        """Test constructing measurement with reflectance category"""
        reflectance_category = Category.objects.create(
            name=CategoryType.REFLECTANCE
        )

        director = MeasurementDirector()
        file_data = {
            "path": (
                "/test/coverage/campaign/point001/reflectancia/"
                "measurement_ref.txt"
            ),
            "name": "measurement_ref.txt",
            "parent": "/test/coverage/campaign/point001",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.category_id == reflectance_category.id

    def test_construct_measurement_unknown_category(self, data_point):
        """Test constructing measurement with unknown category path"""
        director = MeasurementDirector()
        file_data = {
            "path": (
                "/test/coverage/campaign/point001/unknown/"
                "measurement_unknown.txt"
            ),
            "name": "measurement_unknown.txt",
            "parent": "/test/coverage/campaign/point001",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)
        instance = director.commit()

        # Should create without category or with default
        assert instance.id is not None


@pytest.mark.django_db
class TestComplimentaryDirector:
    """Test ComplimentaryDirector class"""

    def test_get_builder_returns_complimentary_builder(self):
        """Test that _get_builder returns ComplimentaryBuilder"""
        director = ComplimentaryDirector()
        from src.campaigns.builders import ComplimentaryBuilder

        assert isinstance(director._builder, ComplimentaryBuilder)

    def test_construct_complimentary_data(self, campaign):
        """Test constructing complimentary data"""
        director = ComplimentaryDirector()
        file_data = {
            "path": "/test/coverage/campaign/fotos/photo001.jpg",
            "name": "photo001.jpg",
            "parent": "/test/coverage/campaign",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)

        assert director._builder.instance.path == (
            "/test/coverage/campaign/fotos/photo001.jpg"
        )
        assert director._builder.instance.name == "photo001.jpg"

    def test_construct_and_commit_complimentary_data(self, campaign):
        """Test full construct and commit flow for complimentary data"""
        director = ComplimentaryDirector()
        file_data = {
            "path": "/test/coverage/campaign/Datos Complementarios/fotos/photo_full.jpg",  # noqa: E501
            "name": "photo_full.jpg",
            "parent": "/test/coverage/campaign",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "metadata": {"camera": "Canon EOS"},
        }
        director.construct(file_data)
        instance = director.commit()

        assert instance.id is not None
        saved = ComplimentaryData.objects.get(
            path="/test/coverage/campaign/Datos Complementarios/fotos/photo_full.jpg"  # noqa: E501
        )
        assert saved.name == "photo_full.jpg"
        assert saved.campaign_id == campaign.id
        assert saved.metadata == {"camera": "Canon EOS"}

    def test_construct_complimentary_field_spreadsheet(self, campaign):
        """Test constructing field spreadsheet complimentary data"""
        director = ComplimentaryDirector()
        file_data = {
            "path": "/test/coverage/campaign/Datos Complementarios/planilla_campo/planilla.xlsx",  # noqa: E501
            "name": "planilla_campo.xlsx",
            "parent": "/test/coverage/campaign",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)
        instance = director.commit()

        assert (
            instance.complement_type == ComplimentaryDataType.FIELD_SPREADSHEET
        )

    def test_construct_complimentary_photos(self, campaign):
        """Test constructing photos complimentary data"""
        director = ComplimentaryDirector()
        file_data = {
            "path": "/test/coverage/campaign/fotos/image.png",
            "name": "image.png",
            "parent": "/test/coverage/campaign",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)
        instance = director.commit()

        assert instance.complement_type == ComplimentaryDataType.PHOTOS


@pytest.mark.django_db
class TestGetDirectorByClassName:
    """Test get_director_by_class_name function"""

    def test_get_unmatched_director(self):
        """Test getting UnmatchedDirector by class name"""
        director_class = get_director_by_class_name("UnmatchedDirector")
        assert director_class == UnmatchedDirector

    def test_get_coverage_director(self):
        """Test getting CoverageDirector by class name"""
        director_class = get_director_by_class_name("CoverageDirector")
        assert director_class == CoverageDirector

    def test_get_campaign_director(self):
        """Test getting CampaignDirector by class name"""
        director_class = get_director_by_class_name("CampaignDirector")
        assert director_class == CampaignDirector

    def test_get_datapoint_director(self):
        """Test getting DataPointDirector by class name"""
        director_class = get_director_by_class_name("DataPointDirector")
        assert director_class == DataPointDirector

    def test_get_measurement_director(self):
        """Test getting MeasurementDirector by class name"""
        director_class = get_director_by_class_name("MeasurementDirector")
        assert director_class == MeasurementDirector

    def test_get_complimentary_director(self):
        """Test getting ComplimentaryDirector by class name"""
        director_class = get_director_by_class_name("ComplimentaryDirector")
        assert director_class == ComplimentaryDirector

    def test_get_invalid_director(self):
        """Test getting invalid director returns None"""
        director_class = get_director_by_class_name("InvalidDirector")
        assert director_class is None

    def test_get_none_director(self):
        """Test getting None director returns None"""
        director_class = get_director_by_class_name(None)
        assert director_class is None


@pytest.mark.django_db
class TestDirectorIntegration:
    """Integration tests for directors"""

    def test_full_hierarchy_construction(self, district):
        """Test constructing full hierarchy from coverage to measurement"""
        # Create coverage
        coverage_director = CoverageDirector()
        coverage_data = {
            "path": "/integration/coverage",
            "name": "Integration Coverage",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }
        coverage_director.construct(coverage_data)
        coverage = coverage_director.commit()

        # Create campaign
        campaign_director = CampaignDirector()
        campaign_data = {
            "path": "/integration/coverage/campaign",
            "name": "Integration Campaign",
            "parent": "/integration/coverage",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "date": "2025-01-15",
            "external_id": "INT001",
            "metadata": {"geo_code": "TEST001"},
        }
        campaign_director.construct(campaign_data)
        campaign = campaign_director.commit()

        # Create data point
        datapoint_director = DataPointDirector()
        datapoint_data = {
            "path": "/integration/coverage/campaign/point001",
            "name": "Point 001",
            "parent": "/integration/coverage/campaign",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "order": "1",
        }
        datapoint_director.construct(datapoint_data)
        datapoint = datapoint_director.commit()

        # Create measurement
        category = Category.objects.create(name=CategoryType.RADIANCE)
        measurement_director = MeasurementDirector()
        measurement_data = {
            "path": (
                "/integration/coverage/campaign/point001/radiancia/"
                "measurement.txt"
            ),
            "name": "measurement.txt",
            "parent": "/integration/coverage/campaign/point001",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }
        measurement_director.construct(measurement_data)
        measurement = measurement_director.commit()

        # Verify relationships
        assert campaign.coverage_id == coverage.id
        assert datapoint.campaign_id == campaign.id
        assert measurement.data_point_id == datapoint.id
        assert measurement.category_id == category.id

    def test_update_existing_with_director(self, coverage):
        """Test updating existing object with director"""
        director = CoverageDirector()
        file_data = {
            "path": "/test/coverage",
            "name": "Updated Name",
            "metadata": {"new_key": "new_value"},
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
        }

        director.construct(file_data)
        updated = director.commit()

        assert updated.id == coverage.id
        assert updated.name == "Updated Name"
        assert "new_key" in updated.metadata

    def test_construct_multiple_objects_same_director(self, coverage):
        """Test constructing multiple objects with same director instance"""
        director = CampaignDirector()

        # First campaign
        data1 = {
            "path": "/test/coverage/campaign1",
            "name": "Campaign 1",
            "parent": "/test/coverage",
            "created_at": datetime(
                2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc
            ),
            "date": "2025-01-15",
            "external_id": "C1",
        }
        director.construct(data1)
        campaign1 = director.commit()

        # Second campaign
        data2 = {
            "path": "/test/coverage/campaign2",
            "name": "Campaign 2",
            "parent": "/test/coverage",
            "created_at": datetime(
                2025, 1, 16, 10, 30, 0, tzinfo=timezone.utc
            ),
            "date": "2025-01-16",
            "external_id": "C2",
        }
        director.construct(data2)
        campaign2 = director.commit()

        assert campaign1.id != campaign2.id
        assert campaign1.name == "Campaign 1"
        assert campaign2.name == "Campaign 2"
