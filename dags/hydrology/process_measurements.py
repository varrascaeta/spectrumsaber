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
        from resources.campaigns.campaign_creators import get_campaign_ids
        from resources.campaigns.measurement_creators import (
            process_measurements
        )
        campaign_ids = get_campaign_ids("HIDROLOGIA")
        process_measurements(campaign_ids)

    # Define flow
    init_file = init_unmatched_file()
    measurements = create_measurements()

    setup_django >> init_file >> measurements


dag = process_hydro_measurements()


if __name__ == "__main__":
    dag.test()
