# Standard imports
import pytest
from io import StringIO
from unittest.mock import MagicMock, patch
import pandas as pd

# Django imports
from django.core.management import call_command

# Project imports
from src.campaigns.models import Campaign, Coverage
from src.places.management.commands.load_places import Command
from src.places.models import Country, District, Province


@pytest.fixture
def country():
    """Create a test country"""
    return Country.objects.create(name="Argentina", code="AR")


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
def sample_excel_data():
    """Create sample Excel data as DataFrame"""
    return pd.DataFrame(
        {
            "Provincia": ["Córdoba", "Buenos Aires", "Santa Fe"],
            "Nombre": ["Capital", "La Plata", "Rosario"],
            "Código": ["COR001", "BUE001", "SFE001"],
        }
    )


@pytest.fixture
def sample_excel_row():
    """Create a single row of Excel data as Series"""
    return pd.Series(
        {"Provincia": "Córdoba", "Nombre": "Capital", "Código": "COR001"}
    )


@pytest.mark.django_db
class TestLoadPlacesCommand:
    """Test load_places management command"""

    def test_command_initialization_creates_argentina(self):
        """Test command __init__ creates Argentina country"""
        # Clear any existing Argentina
        Country.objects.filter(name="Argentina").delete()

        # Initialize command
        command = Command()

        # Verify Argentina was created
        assert Country.objects.filter(name="Argentina", code="AR").exists()
        assert command.country.name == "Argentina"
        assert command.country.code == "AR"

    def test_command_initialization_gets_existing_argentina(self, country):
        """Test command __init__ gets existing Argentina country"""
        initial_count = Country.objects.count()

        # Initialize command
        command = Command()

        # Verify no new country was created
        assert Country.objects.count() == initial_count
        assert command.country.id == country.id

    def test_add_arguments(self):
        """Test command accepts --path argument"""
        command = Command()
        parser = MagicMock()

        command.add_arguments(parser)

        parser.add_argument.assert_called_once_with(
            "--path", type=str, help="Filepath to load"
        )

    @patch("src.places.management.commands.load_places.pd.read_excel")
    @patch("src.places.management.commands.load_places.logger")
    def test_handle_reads_excel_file(self, mock_logger, mock_read_excel):
        """Test handle method reads Excel file from path"""
        mock_read_excel.return_value = pd.DataFrame(
            {
                "Provincia": ["Córdoba"],
                "Nombre": ["Capital"],
                "Código": ["COR001"],
            }
        )

        command = Command()
        command.parse_location = MagicMock()

        command.handle(path="/test/path/places.xlsx")

        mock_read_excel.assert_called_once_with("/test/path/places.xlsx")
        mock_logger.info.assert_any_call(
            "Loading places from %s", "/test/path/places.xlsx"
        )

    @patch("src.places.management.commands.load_places.pd.read_excel")
    def test_handle_processes_all_rows(
        self, mock_read_excel, sample_excel_data
    ):
        """Test handle processes each row in Excel file"""
        mock_read_excel.return_value = sample_excel_data

        command = Command()
        command.parse_location = MagicMock()

        command.handle(path="/test/path/places.xlsx")

        # Verify parse_location called for each row
        assert command.parse_location.call_count == 3

    @patch("src.places.management.commands.load_places.pd.read_excel")
    @patch("src.places.management.commands.load_places.logger")
    def test_handle_logs_processing(
        self, mock_logger, mock_read_excel, sample_excel_data
    ):
        """Test handle logs processing of each row"""
        mock_read_excel.return_value = sample_excel_data

        command = Command()
        command.parse_location = MagicMock()

        command.handle(path="/test/path/places.xlsx")

        # Verify logging calls
        assert mock_logger.info.call_count >= 4  # 1 for loading + 3 for rows
        mock_logger.info.assert_any_call("Processing row %s", 0)
        mock_logger.info.assert_any_call("Processing row %s", 1)
        mock_logger.info.assert_any_call("Processing row %s", 2)

    def test_parse_location_creates_province(self, country, sample_excel_row):
        """Test parse_location creates new province"""
        command = Command()

        command.parse_location(sample_excel_row)

        # Verify province was created
        assert Province.objects.filter(
            name="Córdoba", country=country
        ).exists()

    def test_parse_location_gets_existing_province(
        self, country, province, sample_excel_row
    ):
        """Test parse_location gets existing province"""
        initial_count = Province.objects.count()

        command = Command()
        command.parse_location(sample_excel_row)

        # Verify no new province was created
        assert Province.objects.count() == initial_count

    def test_parse_location_creates_district(self, country, sample_excel_row):
        """Test parse_location creates new district"""
        command = Command()

        command.parse_location(sample_excel_row)

        # Verify district was created
        assert District.objects.filter(name="Capital", code="COR001").exists()

    def test_parse_location_gets_existing_district(
        self, country, province, sample_excel_row
    ):
        """Test parse_location gets existing district"""
        # Create district beforehand
        District.objects.create(
            name="Capital", code="COR001", province=province
        )

        initial_count = District.objects.count()

        command = Command()
        command.parse_location(sample_excel_row)

        # Verify no new district was created
        assert District.objects.count() == initial_count

    @patch("src.places.management.commands.load_places.logger")
    def test_parse_location_logs_district_creation(
        self, mock_logger, country, sample_excel_row
    ):
        """Test parse_location logs district creation"""
        command = Command()

        command.parse_location(sample_excel_row)

        # Verify logging
        district = District.objects.get(code="COR001")
        mock_logger.info.assert_any_call(
            "District %s created: %s", district, True
        )

    @patch("src.places.management.commands.load_places.logger")
    def test_parse_location_logs_district_get(
        self, mock_logger, country, province, sample_excel_row
    ):
        """Test parse_location logs when district already exists"""
        # Create district beforehand
        District.objects.create(
            name="Capital", code="COR001", province=province
        )

        command = Command()
        command.parse_location(sample_excel_row)

        # Verify logging shows created=False
        district = District.objects.get(code="COR001")
        mock_logger.info.assert_any_call(
            "District %s created: %s", district, False
        )

    def test_parse_location_updates_campaigns_with_matching_geo_code(
        self, country, province, coverage, sample_excel_row
    ):
        """Test parse_location updates campaigns with matching geo_code"""
        # Create campaigns with matching geo_code
        campaign1 = Campaign.objects.create(
            name="Campaign 1",
            path="/test/campaign1",
            coverage=coverage,
            district=None,
            metadata={"geo_code": "COR001"},
        )
        campaign2 = Campaign.objects.create(
            name="Campaign 2",
            path="/test/campaign2",
            coverage=coverage,
            district=None,
            metadata={"geo_code": "COR001"},
        )

        command = Command()
        command.parse_location(sample_excel_row)

        # Verify campaigns were updated with district
        campaign1.refresh_from_db()
        campaign2.refresh_from_db()

        district = District.objects.get(code="COR001")
        assert campaign1.district == district
        assert campaign2.district == district

    def test_parse_location_does_not_update_campaigns_with_different_geo_code(
        self, country, province, coverage, sample_excel_row
    ):
        """
        Test parse_location doesn't update campaigns with different geo_code
        """
        # Create campaign with different geo_code
        campaign = Campaign.objects.create(
            name="Campaign",
            path="/test/campaign",
            coverage=coverage,
            district=None,
            metadata={"geo_code": "OTHER001"},
        )

        command = Command()
        command.parse_location(sample_excel_row)

        # Verify campaign was not updated
        campaign.refresh_from_db()
        assert campaign.district is None

    @patch("src.places.management.commands.load_places.logger")
    def test_parse_location_logs_campaign_update_count(
        self, mock_logger, country, province, coverage, sample_excel_row
    ):
        """Test parse_location logs number of campaigns updated"""
        # Create campaigns with matching geo_code
        Campaign.objects.create(
            name="Campaign 1",
            path="/test/campaign1",
            coverage=coverage,
            district=None,
            metadata={"geo_code": "COR001"},
        )
        Campaign.objects.create(
            name="Campaign 2",
            path="/test/campaign2",
            coverage=coverage,
            district=None,
            metadata={"geo_code": "COR001"},
        )

        command = Command()
        command.parse_location(sample_excel_row)

        # Verify logging
        mock_logger.info.assert_any_call("Updating %s campaigns", 2)

    def test_parse_location_updates_campaigns_with_existing_district(
        self, country, province, district, coverage, sample_excel_row
    ):
        """Test parse_location updates campaigns even when district exists"""
        # Create campaign with matching geo_code
        campaign = Campaign.objects.create(
            name="Campaign",
            path="/test/campaign",
            coverage=coverage,
            district=None,
            metadata={"geo_code": "COR001"},
        )

        command = Command()
        command.parse_location(sample_excel_row)

        # Verify campaign was updated
        campaign.refresh_from_db()
        new_district = District.objects.get(code="COR001")
        assert campaign.district == new_district

    def test_parse_location_handles_empty_metadata(
        self, country, coverage, sample_excel_row
    ):
        """Test parse_location handles campaigns with empty metadata"""
        # Create campaign with no metadata
        campaign = Campaign.objects.create(
            name="Campaign",
            path="/test/campaign",
            coverage=coverage,
            district=None,
            metadata={},
        )

        command = Command()
        command.parse_location(sample_excel_row)

        # Verify campaign was not updated (no geo_code match)
        campaign.refresh_from_db()
        assert campaign.district is None

    def test_parse_location_handles_missing_geo_code(
        self, country, coverage, sample_excel_row
    ):
        """
        Test parse_location handles campaigns without geo_code in metadata
        """
        # Create campaign with metadata but no geo_code
        campaign = Campaign.objects.create(
            name="Campaign",
            path="/test/campaign",
            coverage=coverage,
            district=None,
            metadata={"other_field": "value"},
        )

        command = Command()
        command.parse_location(sample_excel_row)

        # Verify campaign was not updated
        campaign.refresh_from_db()
        assert campaign.district is None

    @patch("src.places.management.commands.load_places.pd.read_excel")
    def test_integration_full_command_execution(
        self, mock_read_excel, sample_excel_data, coverage
    ):
        """Integration test: full command execution"""
        mock_read_excel.return_value = sample_excel_data

        # Create campaigns for each district
        Campaign.objects.create(
            name="Campaign Córdoba",
            path="/test/campaign1",
            coverage=coverage,
            metadata={"geo_code": "COR001"},
        )
        Campaign.objects.create(
            name="Campaign Buenos Aires",
            path="/test/campaign2",
            coverage=coverage,
            metadata={"geo_code": "BUE001"},
        )
        Campaign.objects.create(
            name="Campaign Santa Fe",
            path="/test/campaign3",
            coverage=coverage,
            metadata={"geo_code": "SFE001"},
        )

        # Execute command
        out = StringIO()
        call_command("load_places", "--path=/test/places.xlsx", stdout=out)

        # Verify all provinces were created
        assert Province.objects.count() == 3
        assert Province.objects.filter(name="Córdoba").exists()
        assert Province.objects.filter(name="Buenos Aires").exists()
        assert Province.objects.filter(name="Santa Fe").exists()

        # Verify all districts were created
        assert District.objects.count() == 3
        assert District.objects.filter(code="COR001").exists()
        assert District.objects.filter(code="BUE001").exists()
        assert District.objects.filter(code="SFE001").exists()

        # Verify all campaigns were updated
        campaign1 = Campaign.objects.get(name="Campaign Córdoba")
        campaign2 = Campaign.objects.get(name="Campaign Buenos Aires")
        campaign3 = Campaign.objects.get(name="Campaign Santa Fe")

        assert campaign1.district.code == "COR001"
        assert campaign2.district.code == "BUE001"
        assert campaign3.district.code == "SFE001"


@pytest.mark.django_db
class TestLoadPlacesCommandEdgeCases:
    """Test edge cases for load_places command"""

    @patch("src.places.management.commands.load_places.pd.read_excel")
    def test_handle_with_empty_dataframe(self, mock_read_excel):
        """Test handle with empty Excel file"""
        mock_read_excel.return_value = pd.DataFrame(
            {"Provincia": [], "Nombre": [], "Código": []}
        )

        command = Command()
        command.parse_location = MagicMock()

        command.handle(path="/test/empty.xlsx")

        # Verify no rows processed
        command.parse_location.assert_not_called()

    def test_duplicate_code_different_name_update(self, country, province):
        """Test parse_location handles duplicate codes gracefully"""
        # Create district with code
        District.objects.create(
            name="Original Name", code="DUP001", province=province
        )

        # Try to create with same code but different name
        row = pd.Series(
            {
                "Provincia": "Córdoba",
                "Nombre": "Different Name",
                "Código": "DUP001",
            }
        )

        command = Command()
        command.parse_location(row)

        # Verify get_or_create gets existing district
        assert District.objects.filter(code="DUP001").count() == 1
        district = District.objects.get(code="DUP001")
        assert district.name == "Different Name"  # Name updated

    def test_parse_location_with_special_characters(self, country):
        """Test parse_location handles special characters in names"""
        row = pd.Series(
            {
                "Provincia": "Río Negro",
                "Nombre": "San Carlos de Bariloche",
                "Código": "RIO001",
            }
        )

        command = Command()
        command.parse_location(row)

        # Verify province and district created with special characters
        assert Province.objects.filter(name="Río Negro").exists()
        assert District.objects.filter(name="San Carlos de Bariloche").exists()

    @patch("src.places.management.commands.load_places.logger")
    def test_parse_location_logs_zero_campaigns(
        self, mock_logger, country, sample_excel_row
    ):
        """Test parse_location logs when no campaigns match"""
        command = Command()
        command.parse_location(sample_excel_row)

        # Verify logging shows 0 campaigns
        mock_logger.info.assert_any_call("Updating %s campaigns", 0)
