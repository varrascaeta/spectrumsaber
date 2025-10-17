import abc
from src.campaigns.builders import (
    BaseBuilder,
    CoverageBuilder,
    CampaignBuilder,
    DataPointBuilder,
    UnmatchedBuilder
)
from src.campaigns.models import BaseFile
from src.logging_cfg import setup_logger
logger = setup_logger(__name__)

class BaseDirector(abc.ABC):
    def __init__(self):
        self._builder = self._get_builder()

    @abc.abstractmethod
    def _get_builder(self) -> BaseBuilder:
        pass

    def construct(self, file_data: dict) -> BaseFile:
        # Base File attributes
        self._builder.build_instance(path=file_data["path"])
        self._builder.build_name(file_data["name"])
        self._builder.build_metadata(file_data.get("metadata", {}))
        self._builder.build_description(file_data.get("description", ""))
        self._builder.build_ftp_created_at(file_data["created_at"])
        self._builder.build_is_unmatched()
        self._builder.build_last_synced_at()
        self._builder.build_parent(parent_path=file_data.get("parent", ""))

    def commit(self) -> BaseFile:
        self._builder.save_to_db()
        return self._builder.instance


class UnmatchedDirector(BaseDirector):
    def _get_builder(self) -> BaseBuilder:
        return UnmatchedBuilder()

    def construct(self, file_data: dict):
        super().construct(file_data)
        # UnmatchedFile attributes
        self._builder.build_level(file_data.get("level", ""))
        logger.info("Built UnmatchedFile: %s", self._builder.instance.__dict__)


class CoverageDirector(BaseDirector):
    def _get_builder(self) -> BaseBuilder:
        return CoverageBuilder()

    def construct(self, file_data: dict):
        super().construct(file_data)
        # Coverage attributes
        self._builder.build_parent(parent_path="")  # Coverage has no parent


class CampaignDirector(BaseDirector):
    def _get_builder(self) -> BaseBuilder:
        return CampaignBuilder()

    def construct(self, file_data: dict):
        super().construct(file_data)
        # Campaign attributes
        self._builder.build_date(file_data.get("rule_id", ""), file_data.get("date", ""))
        self._builder.build_external_id(file_data.get("external_id", ""))
        self._builder.build_district()
        self._builder.build_measuring_tool()
        self._builder.build_spreadsheets()
        logger.info("Built Campaign: %s", self._builder.instance.__dict__)


class DataPointDirector(BaseDirector):
    def _get_builder(self) -> BaseBuilder:
        return DataPointBuilder()

    def construct(self, file_data: dict) -> BaseFile:
        super().construct(file_data)

        # DataPoint attributes
        self._builder.build_order()

        # Save to DB
        self._builder.save_to_db()
        return self._builder.instance