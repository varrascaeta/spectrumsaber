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
from src.airflow.operators import ScanFTPDirectory, SetupDjango
from src.airflow.tasks import (
    match_patterns,
    select_is_unmatched,
    build_unmatched,
    commit_to_db
)


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
    def build_matched(matched_coverage_data):
        from src.campaigns.directors import CoverageDirector
        logger.info("Building coverage from data %s", matched_coverage_data)
        director = CoverageDirector()
        director.construct(matched_coverage_data)
        pickled_data = pickle.dumps(director)
        encoded_data = base64.b64encode(pickled_data).decode('utf-8')
        return {"director": encoded_data, "class_name": "Coverage"}

    # Define task flow

    apply_rules = match_patterns(
        scan_coverages.output,
        level="coverage"
    )

    unmatched_coverages = select_is_unmatched(
        apply_rules,
        is_unmatched=True
    )

    matched_coverages = select_is_unmatched(
        apply_rules,
        is_unmatched=False
    )

    build_unmatched_coverages = build_unmatched.expand(
        unmatched_file_data=unmatched_coverages
    )

    build_matched_coverages = build_matched.expand(
        matched_coverage_data=matched_coverages
    )

    save_matched_objects = commit_to_db.expand(
        director_data=build_matched_coverages
    )

    save_unmatched_objects = commit_to_db.expand(
        director_data=build_unmatched_coverages
    )

    setup_django >> scan_coverages >> apply_rules
    # Branch for unmatched and matched
    apply_rules >> unmatched_coverages >> build_unmatched_coverages >> save_unmatched_objects
    apply_rules >> matched_coverages >> build_matched_coverages >> save_matched_objects


dag = process_coverage()

if __name__ == "__main__":
    dag.test()
