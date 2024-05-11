# Standard imports
import datetime
import logging
import os
# Project imports
from dags.operators import DjangoOperator, FTPGetterOperator
# Airflow imports
from airflow.decorators import dag, task

logger = logging.getLogger(__name__)
BASE_FTP_PATH = os.getenv("BASE_FTP_PATH")


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
        if Coverage.matches_pattern(coverage_data["name"]):
            coverage, created = Coverage.objects.get_or_create(
                name=coverage_data["name"],
                path=coverage_data["path"],
                created_at=coverage_data["created_at"],
            )
            logger.info(f"{'Created' if created else 'Found'} {coverage}")

    # Define flow
    coverage_data = FTPGetterOperator(
        task_id="get_coverage_data",
        path=BASE_FTP_PATH,
    )
    # Branch for each coverage
    create_coverages = process_coverage.expand(
        coverage_data=coverage_data.output
    )
    setup_django >> coverage_data >> create_coverages


dag = process_coverage()

if __name__ == "__main__":
    dag.test()
