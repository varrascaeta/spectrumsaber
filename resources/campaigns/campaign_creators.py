# Standard imports
import abc
import json
import logging
from datetime import datetime
# Django imports
from django.utils import timezone
# Project imports
from resources.utils import DatabaseContext, FTPClient
from resources.campaigns.models import Campaign, Coverage
from resources.places.models import District
from resources.campaigns.data_point_creators import (
    HydroDataPointCreator,
    UrbanDataPointCreator
)


logger = logging.getLogger(__name__)


# Functions

def get_campaign_ids(coverage_name: str) -> list:
    with DatabaseContext():
        from resources.campaigns.models import Campaign
        campaigns = Campaign.objects.filter(coverage__name=coverage_name)
        return list(campaigns.values_list("id", flat=True))


def process_objects(coverage_tag: str,
                    creator_key: str, parent_ids: list) -> None:
    COVERAGE_MAPPING = {
        "hydro": {
            "campaigns": CampaignCreator,
            "data_points": HydroDataPointCreator,
        },
        "urban": {
            "campaigns": CampaignCreator,
            "data_points": UrbanDataPointCreator,
        }
    }
    with FTPClient() as ftp_client:
        creator_map = COVERAGE_MAPPING[coverage_tag]
        for idx, parent_id in enumerate(parent_ids):
            logger.info("="*80)
            logger.info("Processing %s", creator_key)
            creator = creator_map[creator_key](
                parent_id=parent_id,
                ftp_client=ftp_client
            )
            creator.process()


class CampaignCreator(abc.ABC):
    from resources.utils import FTPClient

    def __init__(self, parent_id: str, ftp_client: FTPClient):
        self.coverage_id = parent_id
        self.ftp_client = ftp_client

    def parse(self, filename: str) -> dict:
        return Campaign.get_attributes_from_name(filename)

    def create_campaign(self, campaign_data: dict):
        parsed_attrs = self.parse(campaign_data["name"])
        if parsed_attrs:
            date = datetime.strptime(parsed_attrs["date_str"], "%Y%m%d").date()
            district = District.objects.filter(
                code=parsed_attrs["geo_code"]
            ).last()
            defaults = {
                "name": campaign_data["name"],
                "ftp_created_at": campaign_data["created_at"],
                "date": date,
                "external_id": parsed_attrs["external_id"],
            }
            if district:
                defaults["district"] = district
            campaign, created = Campaign.objects.update_or_create(
                path=campaign_data["path"],
                coverage_id=self.coverage_id,
                defaults=defaults
            )
            return campaign, created
        else:
            with open("unmatched_campaigns_hydro.txt", "a") as f:
                data = json.dumps(campaign_data, default=str)
                f.write(f"{data}\n")
            return None, False

    def process(self) -> None:
        coverage = Coverage.objects.get(id=self.coverage_id)
        campaign_data = self.ftp_client.get_dir_data(coverage.path)
        for idx, data in enumerate(campaign_data):
            campaign, created = self.create_campaign(data)
            if campaign:
                logger.info(
                    "%s %s (%s/%s)", "Created" if created else "Found",
                    campaign, idx+1, len(campaign_data)
                )
            else:
                logger.info(
                    "Skipping %s (%s/%s)", data['name'], idx+1,
                    len(campaign_data)
                )
        coverage.updated_at = timezone.now()
        coverage.save()
