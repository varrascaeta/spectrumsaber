# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag
# Project imports
from resources.airflow.operators import (
    DatabaseFilterOperator,
    ProcessMeasurementOperator
)


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
    campaigns = DatabaseFilterOperator(
        task_id="get_campaigns_data",
        model_path="resources.campaigns.models.Campaign",
        field="coverage__name",
        value="URBANO",
    )

    measurements = ProcessMeasurementOperator(
        task_id="create_urban_measurements",
        creator_module=(
            "resources.campaigns.measurement_creators.MeasurementCreator"
        ),
        parent_data=campaigns.output,
    )

    campaigns >> measurements


dag = process_urban_measurements()

if __name__ == "__main__":
    dag.test()
