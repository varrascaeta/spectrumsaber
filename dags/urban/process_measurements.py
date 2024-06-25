# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
# Project imports
from dags.operators import DjangoOperator


# Globals
logger = logging.getLogger(__name__)


@dag(
    dag_id="process_urban_measurements",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["measurements", "urban"],
)
def process_urban_measurements() -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def create_measurements() -> None:
        from resources.campaigns.campaign_creators import get_campaign_ids
        from resources.campaigns.measurement_creators import (
            process_measurements
        )
        campaign_ids = get_campaign_ids("URBANO")
        process_measurements(campaign_ids)

    # Define flow
    measurements = create_measurements()

    setup_django >> measurements


dag = process_urban_measurements()


if __name__ == "__main__":
    dag.test()
