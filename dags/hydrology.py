# Standard imports
import sys
import logging
import json
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
from airflow import XComArg
# Project imports
from dags.operators import DjangoOperator, FTPGetterOperator


logger = logging.getLogger(__name__)


@dag(
    dag_id="process_hydro_campaigns",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["campaigns", "hydro"],
)
def process_hydro_campaigns() -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def get_coverage_data() -> dict:
        from resources.campaigns.models import Coverage
        try:
            coverage = Coverage.objects.get(name="HIDROLOGIA")
            return {"id": coverage.id, "path": coverage.path}
        except Coverage.DoesNotExist:
            logger.info(
                "Coverage not found. Try running process_coverage dag first..."
            )

    @task()
    def create_campaign(campaign_data: dict) -> dict:
        from resources.campaigns.models import Campaign
        parsed_attrs = Campaign.get_attributes_from_name(campaign_data["name"])
        if parsed_attrs:
            date = datetime.strptime(parsed_attrs["date_str"], "%Y%m%d").date()
            campaign, created = Campaign.objects.get_or_create(
                name=campaign_data["name"],
                path=campaign_data["path"],
                created_at=campaign_data["created_at"],
                coverage_id=campaign_data["parent"]["id"],
                date=date,
                external_id=parsed_attrs["external_id"],
            )
            logger.info(f"{'Created' if created else 'Found'} {campaign}")
        else:
            logger.info(f"Skipping {campaign_data['name']}")
            with open("unmatched_campaigns_hydro.txt", "a") as f:
                data = json.dumps(campaign_data, default=lambda x: x.__str__())
                f.write(f"{data}\n")

    # Define flow
    coverage_data = get_coverage_data()

    get_hydro_campaigns = FTPGetterOperator(
        task_id="get_hydro_campaings",
        parent_data=coverage_data,
        parent_keys=["id"]
    )
    # Branch for each campaign
    create_campaigns = create_campaign.expand(
        campaign_data=XComArg(get_hydro_campaigns)
    )
    setup_django >> coverage_data >> get_hydro_campaigns >> create_campaigns


@dag(
    dag_id="process_hydro_data_points",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["data_points", "hydro"],
)
def process_hydro_data_points(campaign_ids: list = None) -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def get_campaign_data(campaign_ids: list = None) -> list[dict]:
        from resources.campaigns.models import Campaign
        campaigns = Campaign.objects.filter(coverage__name="HIDROLOGIA")
        if campaign_ids:
            campaigns = campaigns.filter(id__in=campaign_ids)
        if not campaigns.exists():
            msg = (
                "No campaigns found.",
                "Try running process_hydro_campaigns dag first..."
            )
            logger.info(msg)
        else:
            return list(campaigns.values("id", "path"))

    @task()
    def create_data_point(point_data: dict, **kwargs) -> dict:
        from resources.campaigns.models import DataPoint
        parsed_attrs = DataPoint.get_attributes_from_name(point_data["name"])
        if parsed_attrs:
            data_point, created = DataPoint.objects.get_or_create(
                name=point_data["name"],
                path=point_data["path"],
                created_at=point_data["created_at"],
                campaign_id=point_data["parent"]["id"],
                order=parsed_attrs["order"],
            )
            logger.info(f"{'Created' if created else 'Found'} {data_point}")
        else:
            logger.info(f"Skipping {point_data['name']}")
            with open("unmatched_datapoints_hydro.txt", "a") as f:
                data = json.dumps(point_data, default=lambda x: x.__str__())
                f.write(f"{data}\n")

    @task
    def flatten_result(input: list[list[dict]]) -> list[dict]:
        flattened = []
        for item in input:
            flattened.extend(item)
        return flattened

    # Define flow
    campaign_data = get_campaign_data()

    get_data_points = FTPGetterOperator.partial(
        task_id="get_hydro_data_points",
        parent_keys=["id"]
    ).expand(
        parent_data=campaign_data
    )

    flatten_data_points = flatten_result(
        input=XComArg(get_data_points)
    )
    create_data_points = create_data_point.expand(
        point_data=flatten_data_points
    )
    tasks = [
        setup_django,
        campaign_data,
        get_data_points,
        flatten_data_points,
        create_data_points
    ]
    for i in range(1, len(tasks)):
        tasks[i-1] >> tasks[i]


@dag(
    dag_id="process_hydro_measurements",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["measurements", "hydro"],
)
def process_hydro_measurements(data_point_ids: list = None) -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def get_data_points_data(data_point_ids: list = None) -> str:
        from resources.campaigns.models import DataPoint
        if data_point_ids:
            data_points = DataPoint.objects.filter(id__in=data_point_ids)
        else:
            data_points = DataPoint.objects.filter(
                campaign__coverage__name="HIDROLOGIA"
            )
        if not data_points.exists():
            msg = (
                "No data points found for HIDROLOGIA.",
                "Try running process_hydro_data_points dag first..."
            )
            logger.info(msg)
        else:
            return list(data_points.values("id", "path"))

    @task()
    def get_or_create_category(category_data: dict) -> dict:
        from resources.campaigns.models import CategoryType, Category
        category_name = CategoryType.get_by_alias(category_data["name"])
        if category_name:
            category, created = Category.objects.get_or_create(
                name=category_name
            )
            logger.info(f"{'Created' if created else 'Found'} {category}")
            category_data["category_id"] = category.id
            return category_data
        else:
            logger.info(f"Skipping {category_data['name']}")
            with open("unmatched_categories_hydro.txt", "a") as f:
                data = json.dumps(category_data, default=lambda x: x.__str__())
                f.write(f"{data}\n")

    @task()
    def create_measurement(measurement_data: dict, **kwargs) -> None:
        from resources.campaigns.models import Measurement
        measurement, created = Measurement.objects.get_or_create(
            name=measurement_data["name"],
            path=measurement_data["path"],
            created_at=measurement_data["created_at"],
            data_point_id=measurement_data["parent"]["id"],
            category_id=measurement_data["parent"]["category_id"],
        )
        logger.info(f"{'Created' if created else 'Found'} {measurement}")

    @task()
    def flatten_result(input: list[list[dict]]) -> list[dict]:
        flattened = []
        for item in input:
            flattened.extend(item)
        return flattened

    @task.branch()
    def branch_categories(category_data: dict) -> str:
        from resources.campaigns.models import CategoryType
        name = category_data["name"].lower().replace(" ", "")
        category_aliases = CategoryType.SLUG_ALIASES.values()
        if not any([name in aliases for aliases in category_aliases]):
            return "get_subcategories"
        else:
            return "create_categories"

    # Define flow
    data_points_data = get_data_points_data(data_point_ids=data_point_ids)

    get_categories = FTPGetterOperator.partial(
        task_id="get_hydro_categories",
        parent_keys=["id"]
    ).expand(parent_data=data_points_data)

    category_data = flatten_result(input=XComArg(get_categories))

    # Normalize branched categories
    normalize_branch = branch_categories.expand(category_data=category_data)

    get_subcategories = FTPGetterOperator.partial(
        task_id="get_subcategories",
        parent_keys=["parent"]
    ).expand(parent_data=category_data)

    subcategory_data = flatten_result(input=XComArg(get_subcategories))

    create_norm_categories = get_or_create_category.expand(
        category_data=subcategory_data
    )

    get_norm_measurements = FTPGetterOperator.partial(
        task_id="get_normalized_measurements",
        parent_keys=["parent", "category_id"]
    ).expand(parent_data=create_norm_categories)

    norm_measurements_data = flatten_result(
        input=XComArg(get_norm_measurements)
    )

    create_norm_measurements = create_measurement.expand(
        measurement_data=norm_measurements_data
    )

    # Create measurements
    create_categories = get_or_create_category.expand(
        category_data=category_data
    )

    get_measurements = FTPGetterOperator.partial(
        task_id="get_measurements",
        parent_keys=["parent", "category_id"]
    ).expand(parent_data=create_categories)

    measurement_data = flatten_result(input=XComArg(get_measurements))

    create_measurements = create_measurement.expand(
        measurement_data=measurement_data
    )

    # Subcategories flow
    get_subcategories >> subcategory_data >> create_norm_categories
    create_norm_categories >> get_norm_measurements >> norm_measurements_data
    norm_measurements_data >> create_norm_measurements

    # Normal flow
    create_categories >> get_measurements >> measurement_data
    measurement_data >> create_measurements

    # Full flow
    tasks = [
        setup_django,
        data_points_data,
        get_categories,
        category_data,
        normalize_branch,
        [get_subcategories, create_norm_categories],
    ]
    for i in range(1, len(tasks)):
        tasks[i-1] >> tasks[i]


hydro_campaigns = process_hydro_campaigns()
hydro_data_points = process_hydro_data_points()
hydro_measurements = process_hydro_measurements()

if __name__ == "__main__":
    dag_name = sys.argv[1]
    if dag_name == "campaigns":
        hydro_campaigns.test()
    elif dag_name == "data_points":
        hydro_data_points.test()
    elif dag_name == "measurements":
        hydro_measurements.test()
