# Standard imports
import logging
import re
import abc
# Django imports
from django.utils import timezone
# Project imports
from resources.campaigns.models import Campaign, DataPoint


logger = logging.getLogger(__name__)


class DataPointCreator(abc.ABC):
    from resources.utils import FTPClient

    def __init__(self, parent_id: str, ftp_client: FTPClient):
        self.campaign_id = parent_id
        self.order_pattern = r"[0-9_ ]+"
        self.ftp_client = ftp_client

    @abc.abstractmethod
    def is_valid(self, filename: str) -> bool:
        raise NotImplementedError("Subclasses must implement this method")

    @abc.abstractmethod
    def parse(self, filename: str) -> dict:
        raise NotImplementedError("Subclasses must implement this method")

    def create_data_point(self, point_data: dict):
        parsed_attrs = self.parse(point_data["name"])
        is_valid = bool(parsed_attrs != {})
        defaults = {
            "name": point_data["name"],
            "ftp_created_at": point_data["created_at"],
            "is_valid": is_valid,
        }
        if is_valid:
            defaults["order"] = parsed_attrs["order"]
        data_point, created = DataPoint.objects.update_or_create(
            path=point_data["path"],
            campaign_id=self.campaign_id,
            defaults=defaults,
        )
        return data_point, created

    def process(self) -> None:
        campaign = Campaign.objects.get(id=self.campaign_id)
        data_point_data = self.ftp_client.get_dir_data(campaign.path)
        for idx, data in enumerate(data_point_data):
            data_point, created = self.create_data_point(data)
            if data_point:
                logger.info(
                    "%s %s (%s/%s)", "Created" if created else "Found",
                    data_point, idx+1, len(data_point_data)
                )
            else:
                logger.info(
                    "Skipping %s (%s/%s)", data['name'], idx+1,
                    len(data_point_data)
                )
        campaign.updated_at = timezone.now()
        campaign.save()


class HydroDataPointCreator(DataPointCreator):
    def get_order(self, name: str) -> str:
        order_match = re.findall(self.order_pattern, name)
        dirty_order = order_match[0] if order_match else None
        order = dirty_order.split("_")[0] if dirty_order else None
        return order

    def is_valid(self, filename: str) -> bool:
        try:
            cleaned_spaces = filename.replace(" ", "-")
            splitted = cleaned_spaces.split("-")
            right_prefix = splitted[0] == "Punto"
            right_order = self.get_order(splitted[1])
            return right_prefix and right_order is not None
        except Exception as e:
            logger.error(f"Error parsing {filename}: {e}")
            return False

    def parse(self, filename: str) -> dict:
        parsed_attrs = {}
        if self.is_valid(filename):
            order = self.get_order(filename)
            parsed_attrs["order"] = int(order)
        return parsed_attrs


class UrbanDataPointCreator(DataPointCreator):
    def is_valid(self, filename: str) -> bool:
        prefix_pattern = r"L[0-9]+"
        try:
            cleaned_spaces = filename.replace(" ", "-")
            splitted = cleaned_spaces.split("-")
            right_prefix = re.findall(prefix_pattern, splitted[0]) != []
            return right_prefix
        except Exception as e:
            logger.error(f"Error parsing {filename}: {e}")
            return False

    def parse(self, filename: str) -> dict:
        parsed_attrs = {}
        if self.is_valid(filename):
            cleaned_spaces = filename.replace(" ", "-")
            splitted = cleaned_spaces.split("-")
            prefix = splitted[0]
            order = prefix.split("L")[1].strip()
            parsed_attrs = {
                "order": int(order),
            }
        return parsed_attrs
