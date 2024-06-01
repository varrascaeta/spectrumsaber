# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
# Django imports
from django.utils import timezone
# Project imports
from resources.utils import FTPClient, get_campaign_ids
from dags.operators import DjangoOperator


# Globals
logger = logging.getLogger(__name__)


def process_measurements(campaign_ids: list) -> None:
    from resources.campaigns.models import Campaign
    from resources.campaigns.measurement_creators import (
        MeasurementCreator
    )
    with FTPClient() as ftp_client:
        for idx, campaign_id in enumerate(campaign_ids):
            logger.info("="*80)
            logger.info(
                "Processing %s/%s campaign measurements",
                idx + 1,
                len(campaign_ids)
            )
            campaign = Campaign.objects.get(id=campaign_id)
            for data_point in campaign.data_points.all():
                creator = MeasurementCreator(
                    data_point_id=data_point.id,
                    ftp_client=ftp_client
                )
                creator.process()


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
    def create_measurements() -> None:
        campaign_ids = get_campaign_ids("HIDROLOGIA")
        process_measurements(campaign_ids)

    # Define flow
    init_file = init_unmatched_file()
    measurements = create_measurements()

    setup_django >> init_file >> measurements


dag = process_hydro_measurements()


if __name__ == "__main__":
    dag.test()
