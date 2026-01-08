# Standard imports
import pytest
from datetime import date

# Project imports
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
    PATH_LEVELS_MODELS,
    PARENT_MAP,
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
    return District.objects.create(name="Test District", province=province)


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
        date=date(2025, 1, 15),
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
def measurement(data_point, category):
    """Create a test measurement"""
    return Measurement.objects.create(
        name="measurement_001.txt",
        path="/test/coverage/campaign/point001/radiancia/measurement_001.txt",
        data_point=data_point,
        category=category,
    )


@pytest.fixture
def path_rule():
    """Create a test path rule"""
    return PathRule.objects.create(
        name="Test Rule",
        order=1,
        pattern=r"^(?P<name>Point_(?P<metadata__number>\d+))$",
        level="data_point",
    )


@pytest.mark.django_db
class TestCategoryType:
    """Test CategoryType class methods"""

    def test_get_by_alias_radiance(self):
        """Test getting category by radiance alias"""
        result = CategoryType.get_by_alias("radiancia")
        assert result == CategoryType.RADIANCE
        result = CategoryType.get_by_alias("datoradiancia")
        assert result == CategoryType.RADIANCE

    def test_get_by_alias_reflectance(self):
        """Test getting category by reflectance alias"""
        result = CategoryType.get_by_alias("reflectancia")
        assert result == CategoryType.REFLECTANCE
        result = CategoryType.get_by_alias("datoreflectancia")
        assert result == CategoryType.REFLECTANCE

    def test_get_by_alias_avg_radiance(self):
        """Test getting category by average radiance alias"""
        result = CategoryType.get_by_alias("radianciapromedio")
        assert result == CategoryType.AVG_RADIANCE

    def test_get_by_alias_raw_data(self):
        """Test getting category by raw data alias"""
        assert CategoryType.get_by_alias("datocrudo") == CategoryType.RAW_DATA

    def test_get_by_alias_not_found(self):
        """Test getting category with invalid alias returns None"""
        assert CategoryType.get_by_alias("invalid_category") is None

    def test_get_by_path_with_radiance(self):
        """Test getting category from path containing radiance"""
        path = "/coverage/campaign/datapoint/radiancia/file.txt"
        assert CategoryType.get_by_path(path) == CategoryType.RADIANCE

    def test_get_by_path_with_reflectance(self):
        """Test getting category from path containing reflectance"""
        path = "/coverage/campaign/datapoint/reflectancia/file.txt"
        assert CategoryType.get_by_path(path) == CategoryType.REFLECTANCE

    def test_get_by_path_not_found(self):
        """Test getting category from path without category returns None"""
        path = "/coverage/campaign/datapoint/file.txt"
        assert CategoryType.get_by_path(path) is None


@pytest.mark.django_db
class TestComplimentaryDataType:
    """Test ComplimentaryDataType class methods"""

    def test_is_complimentary_with_datos_complementarios(self):
        """Test is_complimentary with 'datos complementarios' in path"""
        path = "/coverage/campaign/datoscomplementarios/file.txt"
        assert ComplimentaryDataType.is_complimentary(path) is True

    def test_is_complimentary_with_fotos(self):
        """Test is_complimentary with 'fotos' alias"""
        path = "/coverage/campaign/fotos/image.jpg"
        assert ComplimentaryDataType.is_complimentary(path) is True

    def test_is_complimentary_with_planilla_campo(self):
        """Test is_complimentary with 'planilla campo' alias"""
        path = "/coverage/campaign/planillacampo/data.xlsx"
        assert ComplimentaryDataType.is_complimentary(path) is True

    def test_get_by_alias_field_spreadsheet(self):
        """Test getting complimentary type by field spreadsheet alias"""
        result = ComplimentaryDataType.get_by_alias("planillacampo")
        assert result == ComplimentaryDataType.FIELD_SPREADSHEET

    def test_get_by_alias_lab_spreadsheet(self):
        """Test getting complimentary type by lab spreadsheet alias"""
        result = ComplimentaryDataType.get_by_alias("planillalaboratorio")
        assert result == ComplimentaryDataType.LAB_SPREADSHEET

    def test_get_by_alias_photos(self):
        """Test getting complimentary type by photos alias"""
        result = ComplimentaryDataType.get_by_alias("fotos")
        assert result == ComplimentaryDataType.PHOTOS

    def test_get_by_alias_not_found(self):
        """Test getting complimentary type with invalid alias returns None"""
        assert ComplimentaryDataType.get_by_alias("invalid") is None

    def test_get_by_path_with_fotos(self):
        """Test getting complimentary type from path with photos"""
        path = "/coverage/campaign/fotos/image.jpg"
        result = ComplimentaryDataType.get_by_path(path)
        assert result == ComplimentaryDataType.PHOTOS

    def test_get_by_path_default(self):
        """Test getting complimentary type from path defaults to
        COMPLIMENTARY_DATA"""
        path = "/coverage/campaign/datoscomplementarios/file.txt"
        result = ComplimentaryDataType.get_by_path(path)
        assert result == ComplimentaryDataType.COMPLIMENTARY_DATA


@pytest.mark.django_db
class TestCategory:
    """Test Category model"""

    def test_create_category(self, category):
        """Test creating a category"""
        assert category.name == CategoryType.RADIANCE
        assert category.created_at is not None

    def test_category_str(self, category):
        """Test category string representation"""
        assert str(category) == CategoryType.RADIANCE

    def test_category_unique_name(self, category):
        """Test category name uniqueness constraint"""
        with pytest.raises(Exception):  # IntegrityError
            Category.objects.create(name=CategoryType.RADIANCE)


@pytest.mark.django_db
class TestCoverage:
    """Test Coverage model"""

    def test_create_coverage(self, coverage):
        """Test creating a coverage"""
        assert coverage.name == "Test Coverage"
        assert coverage.path == "test/coverage"
        assert coverage.scan_complete is False
        assert coverage.is_unmatched is False

    def test_coverage_str(self, coverage):
        """Test coverage string representation"""
        assert str(coverage) == "Test Coverage"

    def test_coverage_unique_path(self, coverage):
        """Test coverage path uniqueness"""
        with pytest.raises(Exception):  # IntegrityError
            Coverage.objects.create(
                name="Another Coverage", path="/test/coverage"
            )

    def test_coverage_auto_timestamps(self, coverage):
        """Test coverage auto timestamps"""
        assert coverage.created_at is not None
        assert coverage.updated_at is not None

    def test_coverage_ordering(self):
        """Test coverage ordering by path"""
        Coverage.objects.create(name="B", path="/b")
        Coverage.objects.create(name="A", path="/a")
        coverages = Coverage.objects.all()
        assert coverages[0].path == "a"
        assert coverages[1].path == "b"


@pytest.mark.django_db
class TestCampaign:
    """Test Campaign model"""

    def test_create_campaign(self, campaign):
        """Test creating a campaign"""
        assert campaign.name == "Test Campaign"
        assert campaign.path == "test/coverage/campaign"
        assert campaign.date == date(2025, 1, 15)
        assert campaign.external_id == "EXT123"

    def test_campaign_str(self, campaign):
        """Test campaign string representation"""
        assert str(campaign) == "Test Campaign"

    def test_campaign_coverage_relationship(self, campaign, coverage):
        """Test campaign-coverage relationship"""
        assert campaign.coverage == coverage
        assert campaign in coverage.campaigns.all()

    def test_campaign_district_relationship(self, campaign, district):
        """Test campaign-district relationship"""
        assert campaign.district == district

    def test_campaign_nullable_district(self, coverage):
        """Test campaign can have null district"""
        campaign = Campaign.objects.create(
            name="Campaign No District",
            path="/test/coverage/campaign2",
            coverage=coverage,
        )
        assert campaign.district is None

    def test_campaign_cascade_delete(self, coverage):
        """Test campaign is deleted when coverage is deleted"""
        campaign = Campaign.objects.create(
            name="Test", path="/test/coverage/test", coverage=coverage
        )
        coverage.delete()
        assert not Campaign.objects.filter(id=campaign.id).exists()


@pytest.mark.django_db
class TestDataPoint:
    """Test DataPoint model"""

    def test_create_data_point(self, data_point):
        """Test creating a data point"""
        assert data_point.name == "Point 001"
        assert data_point.order == 1
        assert data_point.latitude == -31.4201
        assert data_point.longitude == -64.1888

    def test_data_point_str(self, data_point, campaign):
        """Test data point string representation"""
        expected = f"Point 001 | {campaign}"
        assert str(data_point) == expected

    def test_data_point_campaign_relationship(self, data_point, campaign):
        """Test data point-campaign relationship"""
        assert data_point.campaign == campaign
        assert data_point in campaign.data_points.all()

    def test_data_point_cascade_delete(self, campaign):
        """Test data point is deleted when campaign is deleted"""
        dp = DataPoint.objects.create(
            name="Test Point", path="/test/path", campaign=campaign
        )
        campaign.delete()
        assert not DataPoint.objects.filter(id=dp.id).exists()

    def test_data_point_nullable_coordinates(self, campaign):
        """Test data point can have null coordinates"""
        dp = DataPoint.objects.create(
            name="No Coords", path="/test/nocoords", campaign=campaign
        )
        assert dp.latitude is None
        assert dp.longitude is None


@pytest.mark.django_db
class TestMeasurement:
    """Test Measurement model"""

    def test_create_measurement(self, measurement):
        """Test creating a measurement"""
        assert measurement.name == "measurement_001.txt"
        assert measurement.category is not None
        assert measurement.data_point is not None

    def test_measurement_str(self, measurement):
        """Test measurement string representation"""
        assert str(measurement) == "measurement_001.txt"

    def test_measurement_data_point_relationship(
        self, measurement, data_point
    ):
        """Test measurement-data point relationship"""
        assert measurement.data_point == data_point
        assert measurement in data_point.measurements.all()

    def test_measurement_category_relationship(self, measurement, category):
        """Test measurement-category relationship"""
        assert measurement.category == category

    def test_measurement_cascade_delete(self, data_point, category):
        """Test measurement is deleted when data point is deleted"""
        m = Measurement.objects.create(
            name="Test",
            path="/test/measurement",
            data_point=data_point,
            category=category,
        )
        data_point.delete()
        assert not Measurement.objects.filter(id=m.id).exists()


@pytest.mark.django_db
class TestComplimentaryData:
    """Test ComplimentaryData model"""

    def test_create_complimentary_data_with_campaign(self, campaign):
        """Test creating complimentary data linked to campaign"""
        cd = ComplimentaryData.objects.create(
            name="field_data.xlsx",
            path=(
                "/test/coverage/campaign/"
                "datoscomplementarios/field_data.xlsx"
            ),
            campaign=campaign,
            complement_type=ComplimentaryDataType.FIELD_SPREADSHEET,
        )
        assert cd.campaign == campaign
        assert cd.data_point is None
        assert cd.complement_type == ComplimentaryDataType.FIELD_SPREADSHEET

    def test_create_complimentary_data_with_data_point(self, data_point):
        """Test creating complimentary data linked to data point"""
        cd = ComplimentaryData.objects.create(
            name="photo.jpg",
            path=(
                "/test/coverage/campaign/point001/"
                "datoscomplementarios/photo.jpg"
            ),
            data_point=data_point,
            complement_type=ComplimentaryDataType.PHOTOS,
        )
        assert cd.data_point == data_point
        assert cd.complement_type == ComplimentaryDataType.PHOTOS

    def test_get_parent_campaign_level(self, campaign):
        """Test get_parent returns campaign for campaign-level path"""
        path = "/test/coverage/campaign/datoscomplementarios/file.txt"
        parent = ComplimentaryData.get_parent(path)
        assert parent == campaign

    def test_get_parent_data_point_level(self, campaign, data_point):
        """Test get_parent returns data point for data point-level path"""
        path = "/test/coverage/campaign/point001/datoscomplementarios/file.txt"
        parent = ComplimentaryData.get_parent(path)
        assert parent == data_point

    def test_complimentary_data_cascade_delete_campaign(self, campaign):
        """Test complimentary data is deleted when campaign is deleted"""
        cd = ComplimentaryData.objects.create(
            name="Test", path="/test/cd", campaign=campaign
        )
        campaign.delete()
        assert not ComplimentaryData.objects.filter(id=cd.id).exists()


@pytest.mark.django_db
class TestPathRule:
    """Test PathRule model"""

    def test_create_path_rule(self, path_rule):
        """Test creating a path rule"""
        assert path_rule.name == "Test Rule"
        assert path_rule.order == 1
        assert path_rule.level == "data_point"

    def test_path_rule_str(self, path_rule):
        """Test path rule string representation"""
        assert str(path_rule) == "Test Rule"

    def test_match_pattern_success(self, path_rule):
        """Test matching pattern successfully"""
        result = path_rule.match_pattern("Point_123")
        assert result is not None
        assert result["name"] == "Point_123"
        assert result["metadata"]["number"] == "123"

    def test_match_pattern_failure(self, path_rule):
        """Test matching pattern failure"""
        result = path_rule.match_pattern("InvalidName")
        assert result is None

    def test_match_pattern_with_metadata(self):
        """Test matching pattern extracts metadata correctly"""
        rule = PathRule.objects.create(
            name="Metadata Rule",
            order=2,
            pattern=r"^(?P<metadata__campaign>\w+)_(?P<metadata__point>\d+)$",
            level="measurement",
        )
        result = rule.match_pattern("Campaign_001")
        assert result["metadata"]["campaign"] == "Campaign"
        assert result["metadata"]["point"] == "001"

    def test_get_model(self, path_rule):
        """Test get_model returns correct model class"""
        model = path_rule.get_model()
        assert model.__name__ == "DataPoint"

    def test_match_files_with_matching_files(self, path_rule):
        """Test match_files with files that match"""
        files = [
            {
                "name": "Point_001",
                "path": "/test/Point_001",
                "is_unmatched": True,
            },
            {
                "name": "Point_002",
                "path": "/test/Point_002",
                "is_unmatched": True,
            },
        ]
        matched, unmatched = PathRule.match_files(files, "data_point")
        assert len(matched) == 2
        assert len(unmatched) == 0
        assert matched[0]["metadata"]["number"] == "001"
        assert matched[1]["metadata"]["number"] == "002"

    def test_match_files_with_unmatched_files(self, path_rule):
        """Test match_files with files that don't match"""
        files = [
            {
                "name": "Invalid_Name",
                "path": "/test/Invalid_Name",
                "is_unmatched": True,
            },
        ]
        matched, unmatched = PathRule.match_files(files, "data_point")
        assert len(matched) == 0
        assert len(unmatched) == 1
        assert unmatched[0]["is_unmatched"] is True


@pytest.mark.django_db
class TestUnmatchedFile:
    """Test UnmatchedFile model"""

    def test_create_unmatched_file(self, campaign):
        """Test creating an unmatched file"""
        uf = UnmatchedFile.objects.create(
            name="unmatched_point.txt",
            path="/test/coverage/campaign/unmatched_point.txt",
            parent_path="/test/coverage/campaign",
            level="data_point",
            is_unmatched=True,
        )
        assert uf.is_unmatched is True
        assert uf.level == "data_point"
        assert uf.parent_path == "/test/coverage/campaign"

    def test_unmatched_file_manager(self, campaign):
        """Test UnmatchedFile manager filters only unmatched files"""
        UnmatchedFile.objects.create(
            name="matched.txt",
            path="/test/matched.txt",
            parent_path="/test",
            level="campaign",
            is_unmatched=False,
        )
        UnmatchedFile.objects.create(
            name="unmatched.txt",
            path="/test/unmatched.txt",
            parent_path="/test",
            level="campaign",
            is_unmatched=True,
        )
        # Manager should only return unmatched files
        assert UnmatchedFile.objects.count() == 1
        assert UnmatchedFile.objects.first().name == "unmatched.txt"

    def test_create_matched_file_data_point(self, campaign):
        """Test creating matched file from unmatched file"""
        uf = UnmatchedFile.objects.create(
            name="Point_123",
            path="/test/coverage/campaign/Point_123",
            parent_path="/test/coverage/campaign",
            level="data_point",
            is_unmatched=True,
            metadata={"test": "value"},
        )

        attributes = {"order": 5, "latitude": -31.0, "longitude": -64.0}
        matched_file, created = uf.create_matched_file(attributes)

        assert created is True
        assert matched_file is not None
        assert isinstance(matched_file, DataPoint)
        assert matched_file.name == "Point_123"
        assert matched_file.campaign == campaign
        assert matched_file.order == 5
        assert matched_file.is_unmatched is False

    def test_create_matched_file_without_attributes(self, campaign):
        """Test create_matched_file with no attributes returns None"""
        uf = UnmatchedFile.objects.create(
            name="test.txt",
            path="/test/coverage/campaign/test.txt",
            parent_path="/test/coverage/campaign",
            level="data_point",
            is_unmatched=True,
        )

        matched_file, created = uf.create_matched_file(None)
        assert matched_file is None
        assert created is False


@pytest.mark.django_db
class TestBaseFile:
    """Test BaseFile abstract model functionality through concrete models"""

    def test_base_file_match_pattern_with_rule(self, coverage):
        """Test match_pattern method finds matching rule"""
        PathRule.objects.create(
            name="Coverage Rule",
            order=1,
            pattern=r"^(?P<name>Test_(?P<metadata__id>\d+))$",
            level="coverage",
        )

        cov = Coverage.objects.create(name="Test_456", path="/test/Test_456")

        result = cov.match_pattern()
        assert result is not None
        assert result["name"] == "Test_456"
        assert result["metadata"]["id"] == "456"

    def test_base_file_match_pattern_no_match(self, coverage):
        """Test match_pattern returns None when no rule matches"""
        result = coverage.match_pattern()
        assert result is None

    def test_base_file_metadata_field(self, coverage):
        """Test metadata JSON field"""
        coverage.metadata = {"key": "value", "number": 123}
        coverage.save()

        reloaded = Coverage.objects.get(id=coverage.id)
        assert reloaded.metadata["key"] == "value"
        assert reloaded.metadata["number"] == 123

    def test_base_file_optional_fields(self, coverage):
        """Test optional fields can be null"""
        assert coverage.description is None
        assert coverage.metadata is None
        assert coverage.ftp_created_at is None
        assert coverage.last_synced_at is None


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
