# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag
# Project imports
from dags.operators import DatabaseFilterOperator, ProcessObjectsOperator


# Globals
logger = logging.getLogger(__name__)


@dag(
    dag_id="process_hydro_data_points",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["data_points", "hydro"],
)
def process_hydro_data_points() -> None:
    campaigns = DatabaseFilterOperator(
        task_id="get_campaigns_data",
        model_path="resources.campaigns.models.Campaign",
        field="coverage__name",
        value="HIDROLOGIA",
    )

    data_points = ProcessObjectsOperator(
        task_id="create_data_points",
        creator_module=(
            "resources.campaigns.campaign_creators.HydroDataPointCreator"
        ),
        parent_data=campaigns.output,
    )

    campaigns >> data_points


dag = process_hydro_data_points()

if __name__ == "__main__":
    dag.test()
