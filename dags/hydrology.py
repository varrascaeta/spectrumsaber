# Standard imports
import sys
import logging
import json
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
from airflow import XComArg
# Django imports
from django.utils import timezone
# Project imports
from dags.operators import DjangoOperator, FTPGetterOperator
from dags.utils import DatabaseContext


logger = logging.getLogger(__name__)


def get_campaign_ids() -> list:
    with DatabaseContext():
        from resources.campaigns.models import Campaign
        campaigns = Campaign.objects.filter(coverage__name="HIDROLOGIA")
        return list(campaigns.values_list("id", flat=True))


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
    def init_unmatched_file() -> None:
        run_date = timezone.now().strftime("%Y-%m-%d %H:%M:%s")
        with open("unmatched_campaigns_hydro.txt", "a") as f:
            f.write("="*80)
            f.write(f"\nUnmatched campaigns on {run_date}\n")

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
                data = json.dumps(campaign_data, default=str)
                f.write(f"{data}\n")

    # Define flow
    coverage_data = get_coverage_data()

    get_hydro_campaigns = FTPGetterOperator(
        task_id="get_hydro_campaings",
        parent_data=coverage_data,
        parent_keys=["id"]
    )

    init_file = init_unmatched_file()

    # Branch for each campaign
    create_campaigns = create_campaign.expand(
        campaign_data=XComArg(get_hydro_campaigns)
    )
    setup_django >> coverage_data >> get_hydro_campaigns >> init_file
    init_file >> create_campaigns


@dag(
    dag_id="process_hydro_data_points",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["data_points", "hydro"],
)
def process_hydro_data_points() -> None:
    @task()
    def init_unmatched_file() -> None:
        run_date = timezone.now().strftime("%Y-%m-%d %H:%M:%s")
        with open("unmatched_datapoints_hydro.txt", "a") as f:
            f.write("="*80)
            f.write(f"\nUnmatched data points on {run_date}\n")

    @task()
    def create_data_points(campaign_id: int) -> None:
        from resources.campaigns.data_point_creators import (
            HydroDataPointCreator
        )
        creator = HydroDataPointCreator(campaign_id=campaign_id)
        creator.process()

    # Define flow
    init_file = init_unmatched_file()
    campaign_ids = get_campaign_ids()
    data_point_task = create_data_points.expand(campaign_id=campaign_ids)
    init_file >> data_point_task


@dag(
    dag_id="process_hydro_measurements",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["measurements", "hydro"],
)
def process_hydro_measurements() -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def init_unmatched_file() -> None:
        run_date = timezone.now().strftime("%Y-%m-%d %H:%M:%s")
        with open("unmatched_categories_hydro.txt", "a") as f:
            f.write("="*80)
            f.write(f"\nUnmatched categories on {run_date}\n")

    @task()
    def get_data_point_ids(campaign_id: int) -> list:
        from resources.campaigns.models import DataPoint
        data_points = DataPoint.objects.filter(campaign_id=campaign_id)
        return list(data_points.values_list("id", flat=True))

    @task()
    def create_measurements(data_point_id: int) -> None:
        from resources.campaigns.measurement_creators import MeasurementCreator
        creator = MeasurementCreator(data_point_id=data_point_id)
        creator.process()

    # Define flow
    init_file = init_unmatched_file()

    setup_django >> init_file

    campaign_ids = get_campaign_ids()

    for campaign_id in campaign_ids:
        data_point_ids = get_data_point_ids(
            campaign_id=campaign_id
        )
        measurements = create_measurements.expand(
            data_point_id=data_point_ids
        )
        init_file >> data_point_ids >> measurements


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
