# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
# Django imports
from django.utils import timezone
# Project imports
from resources.utils import get_campaign_ids


# Globals
logger = logging.getLogger(__name__)
current_task = 0
total_tasks = 0


@dag(
    dag_id="process_hydro_data_points",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    max_active_tasks=4,
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
        creator = HydroDataPointCreator(
            campaign_id=campaign_id,
        )
        creator.process()
        global current_task, total_tasks
        current_task += 1
        logger.info("="*80)
        logger.info(
            "Processed %s/%s campaign data points",
            current_task,
            total_tasks
        )

    # Define flow
    init_file = init_unmatched_file()
    campaign_ids = get_campaign_ids()
    global total_tasks
    total_tasks = len(campaign_ids)
    for idx, campaign_id in enumerate(campaign_ids):
        data_point_task = create_data_points(
            campaign_id=campaign_id,
        )
        init_file >> data_point_task


dag = process_hydro_data_points()

if __name__ == "__main__":
    dag.test()
