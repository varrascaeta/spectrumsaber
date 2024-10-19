# Standard imports
import datetime
import logging
# Airflow imports
from airflow.decorators import dag, task
# Django imports
from django.conf import settings
# Project imports
from resources.airflow.dags.coverages.builder import CoverageBuilder
from resources.airflow.operators import ScanFTPDirectory


logger = logging.getLogger(__name__)


@dag(
    dag_id="process_coverage",
    schedule=None,
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    tags=["ftp_scanner"],
)
def process_coverage():
    scan_coverage = ScanFTPDirectory(
        task_id="get_coverage_data",
        folder_data={
            "path": settings.BASE_FTP_PATH,
            "is_dir": True,
        }
    )

    @task
    def build_coverage(coverage_data):
        CoverageBuilder().build(coverage_data)

    build_coverages = build_coverage.expand(scan_coverage.output)

    scan_coverage >> build_coverages


dag = process_coverage()

if __name__ == "__main__":
    dag.test()
