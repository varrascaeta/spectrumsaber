# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag
# Project imports
from resources.airflow.operators import (
    DatabaseFilterOperator,
    ProcessObjectsOperator
)


# Globals
logger = logging.getLogger(__name__)


@dag(
    dag_id="process_urban_data_points",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["data_points", "urban"],
)
def process_urban_data_points() -> None:
    campaigns = DatabaseFilterOperator(
        task_id="get_campaigns_data",
        model_path="resources.campaigns.models.Campaign",
        field="coverage__name",
        value="URBANO",
    )

    data_points = ProcessObjectsOperator(
        task_id="create_data_points",
        creator_module=(
            "resources.campaigns.campaign_creators.UrbanDataPointCreator"
        ),
        parent_data=campaigns.output,
    )

    campaigns >> data_points


dag = process_urban_data_points()

if __name__ == "__main__":
    dag.test()
