# Standard imports
import json
import logging
# Project imports
from dags.utils import FTPClient
from resources.campaigns.models import (
    Category, CategoryType, DataPoint, Measurement
)


logger = logging.getLogger(__name__)


class MeasurementCreator:
    def __init__(self, data_point_id: str):
        self.data_point_id = data_point_id
        self.ftp_client = FTPClient()

    def is_category(self, filename: str) -> bool:
        category_aliases = CategoryType.SLUG_ALIASES.values()
        return any([filename in aliases for aliases in category_aliases])

    def get_or_create_category(self, category_data: dict) -> Category:
        category_name = CategoryType.get_by_alias(category_data["name"])
        if category_name:
            category, created = Category.objects.get_or_create(
                name=category_name
            )
            logger.info(f"{'Created' if created else 'Found'} {category}")
            category_data["category_id"] = category.id
            return category
        else:
            logger.info(f"Skipping {category_data['name']}")
            with open("unmatched_categories_hydro.txt", "a") as f:
                data = json.dumps(category_data, default=str)
                f.write(f"{data}\n")

    def get_measurement_data_recursive(self, path: str) -> list:
        final_measurements = []
        name = path.split("/")[-1].lower().replace(" ", "")
        with self.ftp_client as client:
            children_data = client.get_dir_data(path)
        if self.is_category(name):
            category = self.get_or_create_category(children_data)
            if category:
                for child_data in children_data:
                    child_data["category_id"] = category.id
                    final_measurements.append(children_data)
        else:
            for child_data in children_data:
                measurements = self.get_measurement_data_recursive(
                    child_data["path"]
                )
                final_measurements.extend(measurements)
        return final_measurements

    def process(self) -> None:
        data_point = DataPoint.objects.get(id=self.data_point_id)
        measurement_data = self.get_measurement_data_recursive(data_point.path)
        for data in measurement_data:
            measurement, created = Measurement.objects.get_or_create(
                name=data["name"],
                path=data["path"],
                ftp_created_at=data["created_at"],
                data_point_id=self.data_point_id,
                category_id=data["category_id"],
            )
            logger.info(f"{'Created' if created else 'Found'} {measurement}")
