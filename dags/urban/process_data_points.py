# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
# Django imports
from django.utils import timezone
# Project imports
from dags.operators import DjangoOperator

# Globals
logger = logging.getLogger(__name__)


@dag(
    dag_id="process_urban_data_points",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    max_active_tasks=4,
    tags=["data_points", "urban"],
)
def process_urban_data_points() -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def init_unmatched_file() -> None:
        run_date = timezone.now().strftime("%Y-%m-%d %H:%M:%s")
        with open("unmatched_datapoints_urban.txt", "a") as f:
            f.write("="*80)
            f.write(f"\nUnmatched data points on {run_date}\n")

    @task()
    def create_data_points() -> None:
        from resources.campaigns.campaign_creators import (
            get_campaign_ids,
            process_objects
        )
        campaign_ids = get_campaign_ids("URBANO")
        process_objects(
            coverage_tag="urban",
            creator_key="data_points",
            parent_ids=campaign_ids,
        )

    # Define flow
    init_file = init_unmatched_file()
    data_points = create_data_points()

    setup_django >> init_file >> data_points


dag = process_urban_data_points()

if __name__ == "__main__":
    dag.test()
