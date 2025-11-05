# Standard imports
import base64
import datetime
import logging
import pickle

# Django imports
from django.conf import settings

# Airflow imports
from airflow.decorators import dag, task

# Project imports
from src.airflow.operators import ScanFTPDirectory, SetupDjango
from src.airflow.tasks import (
    check_non_empty_dict,
    get_dict_result,
    match_patterns,
    process_expanded_by_class_group,
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
    setup_django = SetupDjango(task_id="setup_django")

    scan_coverages = ScanFTPDirectory(
        task_id="get_coverage_data",
        folder_data={
            "path": settings.BASE_FTP_PATH,
            "is_dir": True,
        },
    )

    @task
    def build_matched(matched_coverage_data):
        from src.campaigns.directors import CoverageDirector

        logger.info("Building coverage from data %s", matched_coverage_data)
        director = CoverageDirector()
        director.construct(matched_coverage_data)
        pickled_data = pickle.dumps(director)
        encoded_data = base64.b64encode(pickled_data).decode("utf-8")
        return {"director": encoded_data, "class_name": "Coverage"}

    # Define task flow

    apply_rules = match_patterns(scan_coverages.output, level="coverage")
    check_matched = check_non_empty_dict(apply_rules, "matched")
    check_unmatched = check_non_empty_dict(apply_rules, "unmatched")

    matched = get_dict_result(apply_rules, "matched")
    unmatched = get_dict_result(apply_rules, "unmatched")

    process_matched = process_expanded_by_class_group(
        "process_matched_coverages", matched, "CoverageDirector"
    )

    process_unmatched = process_expanded_by_class_group(
        "process_unmatched_coverages", unmatched, "UnmatchedDirector"
    )

    (
        setup_django
        >> scan_coverages
        >> apply_rules
        >> [
            check_matched >> process_matched,
            check_unmatched >> process_unmatched,
        ]
    )


dag = process_coverage()

if __name__ == "__main__":
    dag.test()
