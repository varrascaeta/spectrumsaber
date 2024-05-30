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

    def get_or_create_category(self, normalized_name: str) -> Category:
        category_name = CategoryType.get_by_alias(normalized_name)
        if category_name:
            category, created = Category.objects.get_or_create(
                name=category_name
            )
            logger.info(f"{'Created' if created else 'Found'} {category}")
            return category

    def get_measurement_data_recursive(self, path: str,
                                       client: FTPClient) -> list:
        final_measurements = []
        category = None
        children_data = client.get_dir_data(path)
        name = path.split("/")[-1].lower().replace(" ", "")
        if self.is_category(name):
            category = self.get_or_create_category(name)

        for child_data in children_data:
            if category:
                child_data["category_id"] = category.id
                final_measurements.append(child_data)
            elif not child_data["is_dir"]:
                final_measurements.append(child_data)
                with open("unmatched_categories_hydro.txt", "a") as f:
                    data = json.dumps(path, default=str)
                    f.write(f"{data}\n")
            else:
                measurements = self.get_measurement_data_recursive(
                    child_data["path"],
                    client
                )
                final_measurements.extend(measurements)
        return final_measurements

    def process(self) -> None:
        data_point = DataPoint.objects.get(id=self.data_point_id)
        with self.ftp_client as client:
            measurement_data = self.get_measurement_data_recursive(
                data_point.path,
                client
            )
        for data in measurement_data:
            measurement, created = Measurement.objects.get_or_create(
                name=data["name"],
                path=data["path"],
                ftp_created_at=data["created_at"],
                data_point_id=self.data_point_id,
                category_id=data.get("category_id", None),
            )
            logger.info(f"{'Created' if created else 'Found'} {measurement}")
