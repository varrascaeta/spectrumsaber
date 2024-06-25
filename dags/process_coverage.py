# Standard imports
import datetime
import logging
# Project imports
from dags.operators import DjangoOperator, FTPGetterOperator
# Airflow imports
from airflow.decorators import dag, task
from airflow import XComArg
# Django imports
from django.conf import settings


logger = logging.getLogger(__name__)


@dag(
    dag_id="process_coverage",
    schedule=None,
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    tags=["ftp_scanner"],
)
def process_coverage():
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def process_coverage(coverage_data: dict, **kwargs) -> int:
        from resources.campaigns.models import Coverage
        is_valid = Coverage.matches_pattern(coverage_data["name"])
        defaults = {
            "is_valid": is_valid,
            "ftp_created_at": coverage_data["created_at"],
        }
        coverage, created = Coverage.objects.update_or_create(
            name=coverage_data["name"],
            path=coverage_data["path"],
            defaults=defaults
        )
        logger.info(f"{'Created' if created else 'Found'} {coverage}")

    # Define flow
    coverage_data = FTPGetterOperator(
        task_id="get_coverage_data",
        parent_data={"id": None, "path": settings.BASE_FTP_PATH},
        parent_keys=["id"],
    )
    # Branch for each coverage
    create_coverages = process_coverage.expand(
        coverage_data=XComArg(coverage_data)
    )
    setup_django >> coverage_data >> create_coverages


dag = process_coverage()

if __name__ == "__main__":
    dag.test()
