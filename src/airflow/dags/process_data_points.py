# Standard imports
import logging
from datetime import datetime, timedelta

# Airflow imports
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import get_current_context

# Project imports
from src.airflow.operators import ScanFTPDirectory, SetupDjango
from src.airflow.tasks import (
    check_non_empty_dict,
    filter_non_empty,
    match_patterns,
    process_multiple_by_class_group,
)
from src.airflow.utils import get_param_from_context

# Globals
logger = logging.getLogger(__name__)


@dag(
    dag_id="process_data_points",
    schedule=None,
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=["data_points"],
    params={
        "coverage_name": Param(
            type="string",
            description="Name of the coverage to process",
            default="HIDROLOGIA",
        ),
        "force_reprocess": Param(
            type="boolean",
            description="Whether to force reprocessing of data points",
            default=False,
        ),
    },
)
def process_data_points():
    @task
    def get_campaings_to_scan():
        from src.campaigns.models import Campaign

        context = get_current_context()
        coverage_name = get_param_from_context(context, "coverage_name")
        force_reprocess = get_param_from_context(context, "force_reprocess")
        campaigns = Campaign.objects.filter(
            coverage__name=coverage_name,
        )
        if not force_reprocess:
            campaigns = campaigns.filter(scan_complete=False)
        folder_data = [
            {"path": campaign.path, "is_dir": True} for campaign in campaigns
        ]
        logger.info("Found %s campaigns to scan", len(folder_data))
        return folder_data

    @task(trigger_rule="all_done")
    def get_data_points_to_process(dp_data):
        from src.campaigns.models import DataPoint

        paths = [data["path"] for data in dp_data]
        context = get_current_context()
        force_reprocess = get_param_from_context(context, "force_reprocess")
        if force_reprocess:
            logger.info(
                "Force reprocess is enabled, processing all data points"
            )
            return dp_data
        existing = DataPoint.objects.filter(path__in=paths).values_list(
            "path", flat=True
        )
        to_process = [dp for dp in dp_data if dp["path"] not in existing]
        logger.info("Found %s data points to process", len(to_process))
        return to_process

    # Define task flow
    setup_django = SetupDjango(task_id="setup_django")

    campaigns_to_scan = get_campaings_to_scan()

    scan_data_points = ScanFTPDirectory.partial(
        task_id="scan_campaigns", retries=3, retry_delay=timedelta(seconds=30)
    ).expand(folder_data=campaigns_to_scan)

    data_points_to_process = get_data_points_to_process.expand(
        dp_data=scan_data_points.output
    )

    filter_non_empty_dps = filter_non_empty(data_points_to_process)

    splitted = match_patterns.partial(level="data_point").expand(
        file_data=filter_non_empty_dps
    )

    for key, director_class, recurse_dirs in [
        ("matched", "DataPointDirector", False),
        ("unmatched", "UnmatchedDirector", False),
        ("complimentary", "ComplimentaryDirector", True),
    ]:
        check = check_non_empty_dict.partial(key=key).expand(
            dict_data=splitted
        )

        process_task = process_multiple_by_class_group(
            f"process_{key}", recurse_dirs=recurse_dirs
        )

        process = process_task.partial(
            selector_key=key, director_class=director_class
        ).expand(file_data=check)
        splitted >> check >> process

    (
        setup_django
        >> campaigns_to_scan
        >> scan_data_points
        >> data_points_to_process
    )
    data_points_to_process >> filter_non_empty_dps >> splitted


dag = process_data_points()

if __name__ == "__main__":
    params = {"coverage_name": "AGRICULTURA", "force_reprocess": True}
    dag.test(run_conf=params)
