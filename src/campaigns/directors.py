import abc

from src.campaigns.builders import (
    BaseBuilder,
    CampaignBuilder,
    ComplimentaryBuilder,
    CoverageBuilder,
    DataPointBuilder,
    MeasurementBuilder,
    UnmatchedBuilder,
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
        logger.info("Built Coverage: %s", self._builder.instance.__dict__)


class CampaignDirector(BaseDirector):
    def _get_builder(self) -> BaseBuilder:
        return CampaignBuilder()

    def construct(self, file_data: dict):
        super().construct(file_data)
        logger.info("Building Campaign: %s", file_data)
        # Campaign attributes
        self._builder.build_date(
            rule_id=file_data.get("rule_id", ""),
            date_str=file_data.get("date", ""),
        )
        self._builder.build_external_id(file_data.get("external_id", ""))
        self._builder.build_district()
        logger.info("Built Campaign: %s", self._builder.instance.__dict__)


class DataPointDirector(BaseDirector):
    def _get_builder(self) -> BaseBuilder:
        return DataPointBuilder()

    def construct(self, file_data: dict) -> BaseFile:
        super().construct(file_data)

        # DataPoint attributes
        self._builder.build_order(file_data.get("order", 0))
        logger.info("Built DataPoint: %s", self._builder.instance.__dict__)


class MeasurementDirector(BaseDirector):
    def _get_builder(self) -> BaseBuilder:
        return MeasurementBuilder()

    def construct(self, file_data: dict) -> BaseFile:
        super().construct(file_data)

        # Measurement attributes

        self._builder.build_category(file_data["path"])
        logger.info("Built Measurement: %s", self._builder.instance.__dict__)


class ComplimentaryDirector(BaseDirector):
    def _get_builder(self) -> BaseBuilder:
        return (
            ComplimentaryBuilder()
        )  # Assuming ComplimentaryData uses BaseBuilder

    def construct(self, file_data: dict) -> BaseFile:
        super().construct(file_data)
        self._builder.build_complement_type(file_data.get("path"))

        # ComplimentaryData attributes
        logger.info(
            "Built ComplimentaryData: %s", self._builder.instance.__dict__
        )


def get_director_by_class_name(class_name: str):
    director_classes = {
        "UnmatchedDirector": UnmatchedDirector,
        "CoverageDirector": CoverageDirector,
        "CampaignDirector": CampaignDirector,
        "DataPointDirector": DataPointDirector,
        "MeasurementDirector": MeasurementDirector,
        "ComplimentaryDirector": ComplimentaryDirector,
    }
    return director_classes.get(class_name, None)
