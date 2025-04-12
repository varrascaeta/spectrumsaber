
# Standard imports
import abc
import logging
from dateutil.parser import parse
from datetime import datetime, timezone
# Project imports
from resources.campaigns.models import (
    BaseFile,
    Campaign,
    Coverage,
    DataPoint,
    ComplimentaryData
)
from resources.places.models import District


# Globals
logger = logging.getLogger(__name__)


class BaseBuilder(abc.ABC):
    def __init__(self, file_data: dict):
        self.file_data = file_data
        self.file = None
        self.model = self._get_model()
        self.is_unmatched = False
        self.result = {}

    def build(self) -> dict:
        name = self.file_data["name"]
        if not self.model.matches_pattern(name):
            self.is_unmatched = True
        self.result = {
            "name": name,
            "path": self.file_data["path"],
            "defaults": {
                "ftp_created_at": self.file_data["created_at"],
                "is_unmatched": self.is_unmatched,
                "last_synced_at": None,
            },
        }

    def save_to_db(self) -> BaseFile:
        self.result["defaults"]["last_synced_at"] = datetime.now(timezone.utc)
        file, created = self.model.objects.update_or_create(
            **self.result
        )
        status = "Created" if created else "Updated"
        logger.info("%s file %s", status, file.name)
        self.file = file

    def _get_model(self) -> BaseFile:
        return BaseFile

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state


class CoverageBuilder(BaseBuilder):
    def _get_model(self):
        return Coverage


class CampaignBuilder(BaseBuilder):
    def _get_model(self):
        return Campaign

    def build_parent(self, coverage_name: str) -> int:
        coverage_id = Coverage.objects.get(name=coverage_name).id
        self.result["coverage_id"] = coverage_id

    def build_metadata(self):
        if self.is_unmatched:
            logger.info("Can't build metadata for unmatched file")
            return
        name_attrs = Campaign.get_attributes_from_name(self.file_data["name"])
        self.result["metadata"] = name_attrs

    def build_date(self):
        if self.is_unmatched:
            logger.info("Can't build date for unmatched file")
            return
        date_str = self.result["metadata"].get("date")
        if date_str:
            self.result["date"] = parse(date_str)

    def build_external_id(self):
        if self.is_unmatched:
            logger.info("Can't build external_id for unmatched file")
            return
        external_id = self.result["metadata"].get("external_id")
        if external_id:
            self.result["external_id"] = external_id

    def build_location(self):
        if self.is_unmatched:
            logger.info("Can't build location for unmatched file")
            return
        district_code = self.result["metadata"].get("geo_code")
        if district_code:
            district = District.objects.filter(code=district_code).last()
            if district:
                self.result["district_id"] = district.id


class DataPointBuilder(BaseBuilder):
    def _get_model(self):
        return DataPoint

    def build_parent(self) -> int:
        parent_path = self.file_data.get("parent")
        if parent_path:
            parent = Campaign.objects.filter(path=parent_path).last()
            if parent:
                self.result["campaign_id"] = parent.id

    def build_metadata(self):
        if self.is_unmatched:
            logger.info("Can't build metadata for unmatched file")
            return
        name_attrs = DataPoint.get_attributes_from_name(self.file_data["name"])
        self.result["metadata"] = name_attrs

    def build_order(self):
        if self.is_unmatched:
            self.result["order"] = 0
            return
        order = self.result["metadata"].get("order")
        if order:
            self.result["order"] = order


class ComplimentaryDataBuilder(BaseBuilder):
    def _get_model(self):
        return ComplimentaryData

    def build_parent(self) -> int: 
        parent_path = self.file_data.get("parent")
        if parent_path:
            parent = Campaign.objects.filter(path=parent_path).last()
            if parent:
                self.result["campaign_id"] = parent.id