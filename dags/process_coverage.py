# Standard imports
import datetime
import logging
import json
# Airflow imports
from airflow.decorators import dag
# Django imports
from django.conf import settings
# Project imports
from dags.operators import DjangoOperator, FTPGetterOperator


logger = logging.getLogger(__name__)


class CreateCoverageOperator(DjangoOperator):
    def __init__(self, coverage_data, **kwargs):
        super().__init__(**kwargs)
        self.coverage_data = coverage_data

    def execute(self, context):
        from resources.campaigns.models import Coverage
        if Coverage.matches_pattern(self.coverage_data["name"]):
            defaults = {
                "ftp_created_at": self.coverage_data["created_at"],
            }
            coverage, created = Coverage.objects.update_or_create(
                name=self.coverage_data["name"],
                path=self.coverage_data["path"],
                defaults=defaults,
            )
            logger.info(f"{'Created' if created else 'Found'} {coverage}")
        else:
            with open("unmatched_coverages.txt", "a") as f:
                data = json.dumps(self.coverage_data, default=str)
                f.write(f"{data}\n")


@dag(
    dag_id="process_coverage",
    schedule=None,
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    tags=["ftp_scanner"],
)
def process_coverage():
    # Define flow
    coverage_data = FTPGetterOperator(
        task_id="get_coverage_data",
        parent_data={"id": None, "path": settings.BASE_FTP_PATH},
        parent_keys=["id"],
    )
    # Branch for each coverage
    create_coverages = CreateCoverageOperator.partial(
        task_id="create_coverage"
    ).expand(
        coverage_data=coverage_data.output
    )

    coverage_data >> create_coverages


dag = process_coverage()

if __name__ == "__main__":
    dag.test()
