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
    dag_id="process_hydro_data_points",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    max_active_tasks=4,
    tags=["data_points", "hydro"],
)
def process_hydro_data_points() -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def init_unmatched_file() -> None:
        run_date = timezone.now().strftime("%Y-%m-%d %H:%M:%s")
        with open("unmatched_datapoints_hydro.txt", "a") as f:
            f.write("="*80)
            f.write(f"\nUnmatched data points on {run_date}\n")

    @task()
    def create_data_points() -> None:
        from resources.campaigns.campaign_creators import (
            process_objects,
            get_campaign_ids
        )
        campaign_ids = get_campaign_ids("HIDROLOGIA")
        process_objects(
            coverage_tag="hydro",
            creator_key="data_points",
            parent_ids=campaign_ids,
        )

    # Define flow
    init_file = init_unmatched_file()
    data_points = create_data_points()

    setup_django >> init_file >> data_points


dag = process_hydro_data_points()

if __name__ == "__main__":
    dag.test()
