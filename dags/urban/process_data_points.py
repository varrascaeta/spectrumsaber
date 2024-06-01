# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
# Django imports
from django.utils import timezone
# Project imports
from resources.utils import get_campaign_ids, FTPClient


# Globals
logger = logging.getLogger(__name__)


def process_data_points(campaign_ids: list) -> None:
    from resources.campaigns.data_point_creators import (
        UrbanDataPointCreator
    )
    with FTPClient() as ftp_client:
        for idx, campaign_id in enumerate(campaign_ids):
            logger.info("="*80)
            logger.info(
                "Processing %s/%s campaign data points",
                idx + 1,
                len(campaign_ids)
            )
            creator = UrbanDataPointCreator(
                campaign_id=campaign_id,
                ftp_client=ftp_client
            )
            creator.process()


@dag(
    dag_id="process_urban_data_points",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    max_active_tasks=4,
    tags=["data_points", "urban"],
)
def process_urban_data_points() -> None:
    @task()
    def init_unmatched_file() -> None:
        run_date = timezone.now().strftime("%Y-%m-%d %H:%M:%s")
        with open("unmatched_datapoints_urban.txt", "a") as f:
            f.write("="*80)
            f.write(f"\nUnmatched data points on {run_date}\n")

    @task()
    def create_data_points() -> None:
        campaign_ids = get_campaign_ids("URBANO")
        process_data_points(campaign_ids)

    # Define flow
    init_file = init_unmatched_file()
    data_points = create_data_points()
    init_file >> data_points


dag = process_urban_data_points()

if __name__ == "__main__":
    dag.test()
