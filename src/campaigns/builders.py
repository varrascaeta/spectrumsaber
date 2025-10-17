
# Standard imports
import abc
import logging
from dateutil.parser import parse
from datetime import datetime, timezone
# Project imports
from src.campaigns.models import (
    BaseFile,
    Campaign,
    Coverage,
    DataPoint,
    ComplimentaryData
)
from src.places.models import District


# Globals
logger = logging.getLogger(__name__)


class BaseBuilder(abc.ABC):
    def __init__(self):
        self.model = self._get_model()
        self.instance = None
        self.attributes = {}

    def build_instance(self, path: str) -> BaseFile:
        existing = self.model.objects.filter(path=path).first()
        if existing:
            self.instance = existing
        else:
            self.instance = self.model(path=path)

    def build_name(self, name: str):
        self.instance.name = name

    def build_description(self, description: str):
        self.instance.description = description

    def build_ftp_created_at(self, created_at: str):
        if not self.instance.ftp_created_at and created_at:
            self.instance.ftp_created_at = created_at

    def build_is_unmatched(self):
        if not self.attributes:
            self.instance.is_unmatched = True
            logger.warning(f"File {self.instance.name} is unmatched")

    def build_last_synced_at(self):
        self.instance.last_synced_at = datetime.now(timezone.utc)

    def build_attributes(self):
        if not self.instance.name:
            logger.error("Name is not set for the instance")
            return
        attributes = self.instance.match_pattern()
        self.attributes.update(attributes or {})

    def build_metadata(self):
        self.instance.metadata = self.attributes.get("metadata", {})

    @abc.abstractmethod
    def build_parent(self, parent_path: str):
        pass

    def save_to_db(self) -> BaseFile:
        self.instance.save()
        return self.instance

    @abc.abstractmethod
    def _get_model(self) -> BaseFile:
        return BaseFile

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state


class CoverageBuilder(BaseBuilder):
    def _get_model(self):
        return Coverage

    def build_parent(self, parent_path: str) -> int:
        # Coverage has no parent
        pass


class CampaignBuilder(BaseBuilder):
    def _get_model(self):
        return Campaign

    def build_date(self):
        date_str = self.attributes.get("date")
        if date_str:
            self.instance.date = parse(date_str)

    def build_external_id(self):
        self.instance.external_id = self.attributes.get("external_id")

    def build_parent(self, parent_path: str):
        coverage_id = Coverage.objects.get(path=parent_path).id
        self.instance.coverage_id = coverage_id

    def build_district(self):
        district_code = self.attributes.get("geo_code")
        if district_code:
            district = District.objects.filter(code=district_code).last()
            if district:
                self.instance.district_id = district.id

    def build_measuring_tool(self):
        pass

    def build_spreadsheets(self):
        pass


class DataPointBuilder(BaseBuilder):
    def _get_model(self):
        return DataPoint

    def build_parent(self, parent_path: str):
        parent = Campaign.objects.get(path=parent_path)
        self.instance.campaign_id = parent.id

    def build_order(self):
        order = self.attributes.get("order")
        if order:
            self.instance.order = int(order)

    def build_latitude(self):
        latitude = self.attributes.get("latitude")
        if latitude:
            self.instance.latitude = float(latitude)

    def build_longitude(self):
        longitude = self.attributes.get("longitude")
        if longitude:
            self.instance.longitude = float(longitude)


class ComplimentaryDataBuilder(BaseBuilder):
    def _get_model(self):
        return ComplimentaryData

    def build_parent(self) -> int: 
        parent_path = self.file_data.get("parent")
        if parent_path:
            parent = Campaign.objects.filter(path=parent_path).last()
            if parent:
                self.result["campaign_id"] = parent.id


