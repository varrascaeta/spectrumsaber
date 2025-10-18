
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
    ComplimentaryData,
    PathRule,
    UnmatchedFile
)
from src.places.models import District
from src.campaigns.models import PATH_LEVELS


# Globals
logger = logging.getLogger(__name__)

DATE_TRANSLATE = {
    "ene": "jan",
    "feb": "feb",
    "mar": "mar",
    "abr": "apr",
    "may": "may",
    "jun": "jun",
    "jul": "jul",
    "ago": "aug",
    "set": "sep",
    "oct": "oct",
    "nov": "nov",
    "dic": "dec",
}


class BaseBuilder(abc.ABC):
    def __init__(self):
        self.model = self._get_model()
        self.instance = None

    def remove_unmatched_if_exists(self, path: str):
        unmatched = UnmatchedFile.objects.filter(path=path).first()
        if unmatched:
            unmatched.delete()

    def build_instance(self, path: str):
        self.remove_unmatched_if_exists(path)
        existing = self.model.objects.filter(path=path).first()
        if existing:
            self.instance = existing
        else:
            self.instance = self.model(path=path)

    def build_name(self, name: str):
        self.instance.name = name

    def build_metadata(self, metadata: dict):
        if self.instance.metadata:
            self.instance.metadata.update(metadata)
        else:
            self.instance.metadata = metadata

    def build_description(self, description: str):
        self.instance.description = description

    def build_ftp_created_at(self, created_at: str):
        if not self.instance.ftp_created_at and created_at:
            self.instance.ftp_created_at = created_at

    def build_is_unmatched(self):
        self.instance.is_unmatched = False

    def build_last_synced_at(self):
        self.instance.last_synced_at = datetime.now(timezone.utc)

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


class UnmatchedBuilder(BaseBuilder):
    def _get_model(self):
        return UnmatchedFile

    def remove_unmatched_if_exists(self, path: str):
        # No need to remove unmatched for unmatched files
        pass

    def build_parent(self, parent_path: str):
        self.instance.parent_path = parent_path

    def build_is_unmatched(self):
        self.instance.is_unmatched = True

    def build_level(self, level: str):
        if level in dict(PATH_LEVELS).keys():
            self.instance.level = level


class CoverageBuilder(BaseBuilder):
    def _get_model(self):
        return Coverage

    def build_parent(self, parent_path: str) -> int:
        # Coverage has no parent
        pass


class CampaignBuilder(BaseBuilder):
    def _get_model(self):
        return Campaign

    def _translate_date_str(self, date_str: str) -> str:
        date_str = date_str.lower()
        for es_month, en_month in DATE_TRANSLATE.items():
            date_str = date_str.replace(es_month, en_month)
        return date_str

    def build_date(self, rule_id: int, date_str: str):
        date = None
        if date_str:
            date_str = self._translate_date_str(date_str)
            try:
                rule = PathRule.objects.get(id=rule_id)
                if rule.date_format:
                    date = datetime.strptime(date_str, rule.date_format)
                else:
                    date = parse(date_str)
            except ValueError as e:
                try:
                    date = parse(date_str)
                except Exception as e:
                    logger.warning("Failed to parse date '%s': %s", date_str, e)
        self.instance.date = date

    def build_external_id(self, external_id: str):
        self.instance.external_id = external_id

    def build_parent(self, parent_path: str):
        coverage_id = Coverage.objects.get(path=parent_path).id
        self.instance.coverage_id = coverage_id

    def build_district(self):
        district_code = self.instance.metadata.get("geo_code")
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

    def build_order(self, order: str = None):
        self.instance.order = int(order) if order else 0

    def build_latitude(self):
        latitude = self.instance.metadata.get("latitude")
        if latitude:
            self.instance.latitude = float(latitude)

    def build_longitude(self):
        longitude = self.instance.metadata.get("longitude")
        if longitude:
            self.instance.longitude = float(longitude)


class ComplimentaryDataBuilder(BaseBuilder):
    def _get_model(self):
        return ComplimentaryData
