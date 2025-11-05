# Standard imports
import pytest

# Project imports
from src.campaigns.models import Campaign


@pytest.mark.django_db
class TestCampaignModel:
    def test_get_attributes_from_name(self):
        campaign = Campaign.get_attributes_from_name("136-20220401-COR")
        assert campaign == {
            "date_str": "20220401",
            "external_id": "136",
            "geo_code": "COR",
        }

    def test_missing_geo(self):
        campaign = Campaign.get_attributes_from_name("136-20220401")
        assert not campaign

    def test_too_much_args(self):
        campaign = Campaign.get_attributes_from_name("136-20220401-COR-")
        assert campaign == {
            "date_str": "20220401",
            "external_id": "136",
            "geo_code": "COR",
        }

    def test_wrong_prefix(self):
        campaign = Campaign.get_attributes_from_name("HIDROLOGIA-20220401-COR")
        assert not campaign

    def test_wrong_date(self):
        campaign = Campaign.get_attributes_from_name("136-2022041-COR")
        assert not campaign
