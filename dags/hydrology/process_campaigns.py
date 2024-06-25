# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
# Project imports
from dags.operators import DjangoOperator


# Globals
logger = logging.getLogger(__name__)
current_task = 0
total_tasks = 0


@dag(
    dag_id="process_hydro_campaigns",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["campaigns", "hydro"],
)
def process_hydro_campaigns() -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def get_coverage_data() -> dict:
        from resources.campaigns.models import Coverage
        try:
            coverage = Coverage.objects.get(name="HIDROLOGIA")
            return {"id": coverage.id, "path": coverage.path}
        except Coverage.DoesNotExist:
            logger.info(
                "Coverage not found. Try running process_coverage dag first..."
            )

    @task()
    def create_campaigns(coverage_data: dict) -> None:
        from resources.campaigns.campaign_creators import process_objects
        if coverage_data:
            process_objects(
                coverage_tag="hydro",
                creator_key="campaigns",
                parent_ids=[coverage_data["id"]],
            )

    # Define flow
    coverage_data = get_coverage_data()
    campaigns = create_campaigns(coverage_data=coverage_data)

    setup_django >> coverage_data >> campaigns


dag = process_hydro_campaigns()

if __name__ == "__main__":
    dag.test()
