# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
# Django imports
from django.utils import timezone
# Project imports
from resources.utils import get_campaign_ids
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
    def create_measurements(data_point_id: int) -> None:
        from resources.campaigns.measurement_creators import MeasurementCreator
        creator = MeasurementCreator(data_point_id=data_point_id)
        creator.process()
        global current_task, total_tasks
        current_task += 1
        logger.info("="*80)
        logger.info(
            "Processed %s/%s campaign measurements",
            current_task,
            total_tasks
        )

    # Define flow
    init_file = init_unmatched_file()

    setup_django >> init_file

    campaign_ids = get_campaign_ids()
    global total_tasks, current_task
    total_tasks = len(campaign_ids)
    current_task = 0
    for campaign_id in campaign_ids:
        data_point_ids = get_data_point_ids(
            campaign_id=campaign_id
        )
        measurements = create_measurements.expand(
            data_point_id=data_point_ids
        )
        init_file >> data_point_ids >> measurements


dag = process_hydro_measurements()


if __name__ == "__main__":
    dag.test()
