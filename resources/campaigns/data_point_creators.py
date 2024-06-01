# Standard imports
import json
import logging
import re
import abc
# Django imports
from django.utils import timezone
# Project imports
from resources.utils import FTPClient
from resources.campaigns.models import Campaign, DataPoint


logger = logging.getLogger(__name__)


class DataPointCreator(abc.ABC):
    def __init__(self, campaign_id: str, ftp_client: FTPClient):
        self.campaign_id = campaign_id
        self.order_pattern = r"[0-9_ ]+"
        self.dirty_order = ""
        self.parsed_attrs = {}
        self.ftp_client = ftp_client

    @abc.abstractmethod
    def is_valid(self, filename: str) -> bool:
        raise NotImplementedError("Subclasses must implement this method")

    @abc.abstractmethod
    def parse(self, filename: str) -> dict:
        raise NotImplementedError("Subclasses must implement this method")

    def create_data_point(self, point_data: dict):
        parsed_attrs = self.parse(point_data["name"])
        if parsed_attrs:
            defaults = {
                "ftp_created_at": point_data["created_at"],
                "order": parsed_attrs["order"],
            }
            data_point, created = DataPoint.objects.update_or_create(
                name=point_data["name"],
                path=point_data["path"],
                campaign_id=self.campaign_id,
                defaults=defaults,
            )
            logger.info(f"{'Created' if created else 'Found'} {data_point}")
        else:
            logger.info(f"Skipping {point_data['name']}")
            with open("unmatched_datapoints_hydro.txt", "a") as f:
                data = json.dumps(point_data, default=str)
                f.write(f"{data}\n")

    def process(self) -> None:
        campaign = Campaign.objects.get(id=self.campaign_id)
        data_point_data = self.ftp_client.get_dir_data(campaign.path)
        for data in data_point_data:
            self.create_data_point(data)
        campaign.updated_at = timezone.now()
        campaign.save()


class HydroDataPointCreator(DataPointCreator):
    def is_valid(self, filename: str) -> bool:
        try:
            cleaned_spaces = filename.replace(" ", "-")
            splitted = cleaned_spaces.split("-")
            right_prefix = splitted[0] == "Punto"
            order_match = re.findall(self.order_pattern, splitted[1])
            self.dirty_order = order_match[0] if order_match else ""
            right_order = len(order_match) > 0
            return right_prefix and right_order
        except Exception as e:
            logger.error(f"Error parsing {filename}: {e}")
            return False

    def parse(self, filename: str) -> dict:
        parsed_attrs = {}
        if self.is_valid(filename):
            order = self.dirty_order.split("_")[0]
            parsed_attrs["order"] = int(order)
        return parsed_attrs
