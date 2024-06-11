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
current_task = 0
total_tasks = 0


@dag(
    dag_id="process_urban_campaigns",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["campaigns", "urban"],
)
def process_urban_campaigns() -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def init_unmatched_file() -> None:
        run_date = timezone.now().strftime("%Y-%m-%d %H:%M:%s")
        with open("unmatched_campaigns_urban.txt", "a") as f:
            f.write("="*80)
            f.write(f"\nUnmatched campaigns on {run_date}\n")

    @task()
    def get_coverage_data() -> dict:
        from resources.campaigns.models import Coverage
        try:
            coverage = Coverage.objects.get(name="URBANO")
            return {"id": coverage.id, "path": coverage.path}
        except Coverage.DoesNotExist:
            logger.info(
                "Coverage not found. Try running process_coverage dag first..."
            )

    @task()
    def create_campaigns(coverage_data: dict) -> None:
        from resources.campaigns.campaign_creators import process_objects
        process_objects(
            coverage_tag="urban",
            creator_key="campaigns",
            parent_ids=[coverage_data["id"]],
        )

    # Define flow
    coverage_data = get_coverage_data()
    init_file = init_unmatched_file()
    campaigns = create_campaigns(coverage_data=coverage_data)

    setup_django >> coverage_data >> init_file >> campaigns


dag = process_urban_campaigns()

if __name__ == "__main__":
    dag.test()
