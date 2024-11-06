# Standard imports
import base64
import datetime
import logging
import pickle
# Airflow imports
from airflow.decorators import dag, task
# Django imports
from django.conf import settings
# Project imports
from resources.airflow.operators import ScanFTPDirectory, SetupDjango


logger = logging.getLogger(__name__)


@dag(
    dag_id="process_coverage",
    schedule=None,
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    tags=["ftp_scanner"],
)
def process_coverage():
    setup_django = SetupDjango(
        task_id="setup_django"
    )

    scan_coverages = ScanFTPDirectory(
        task_id="get_coverage_data",
        folder_data={
            "path": settings.BASE_FTP_PATH,
            "is_dir": True,
        }
    )

    @task
    def build_coverage(coverage_data):
        from resources.airflow.dags.builder import CoverageBuilder
        builder = CoverageBuilder(coverage_data)
        builder.build()
        if not builder.result:
            return None
        pickled_data = pickle.dumps(builder)
        encoded_data = base64.b64encode(pickled_data).decode('utf-8')
        return {"builder": encoded_data}

    @task
    def save_coverage(coverage_builder):
        encoded_data = coverage_builder['builder'].encode('utf-8')
        pickled_data = base64.b64decode(encoded_data)
        builder = pickle.loads(pickled_data)
        builder.save_to_db()

    build_coverages = build_coverage.expand(
        coverage_data=scan_coverages.output
    )

    save_coverages = save_coverage.expand(
        coverage_builder=build_coverages
    )

    setup_django >> scan_coverages >> build_coverages >> save_coverages


dag = process_coverage()

if __name__ == "__main__":
    dag.test()
