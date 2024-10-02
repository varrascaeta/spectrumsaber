# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag
# Project imports
from dags.operators import ProcessObjectsOperator, DatabaseFilterOperator


# Globals
logger = logging.getLogger(__name__)


@dag(
    dag_id="process_hydro_campaigns",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["campaigns", "hydro"],
)
def process_hydro_campaigns() -> None:
    coverage_data = DatabaseFilterOperator(
        task_id="get_coverage_data",
        model_path="resources.campaigns.models.Coverage",
        field="name",
        value="HIDROLOGIA",
    )

    campaigns = ProcessObjectsOperator(
        task_id="create_campaigns",
        creator_module="resources.campaigns.campaign_creators.CampaignCreator",
        parent_data=coverage_data.output,
    )

    coverage_data >> campaigns


dag = process_hydro_campaigns()

if __name__ == "__main__":
    dag.test()
