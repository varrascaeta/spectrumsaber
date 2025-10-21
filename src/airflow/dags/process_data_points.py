# Standard imports
import logging
import pickle
import base64
from datetime import datetime, timedelta
# Airflow imports
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import get_current_context
# Project imports
from src.airflow.operators import (
    ScanFTPDirectory,
    SetupDjango
)
from src.utils import get_param_from_context
from src.airflow.tasks import (
    match_patterns
)


# Globals
logger = logging.getLogger(__name__)
coverage_param = "{{ params.coverage_name }}"


@dag(
    dag_id="process_data_points",
    schedule=None,
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=["data_points"],
    params={
        "coverage_name": Param(
            description="Name of the coverage to process",
            default="HIDROLOGIA"
        ),
        "force_reprocess": Param(
            description="Whether to force reprocessing of data points",
            default=False
        )
    }

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
            is_unmatched=False
        )
        if not force_reprocess:
            campaigns = campaigns.filter(scan_complete=True)
        folder_data = [
            {"path": campaign.path, "is_dir": True}
            for campaign in campaigns
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
            logger.info("Force reprocess is enabled, processing all data points")
            return dp_data
        existing = DataPoint.objects.filter(path__in=paths).values_list(
            "path",
            flat=True
        )
        to_process = [
            dp for dp in dp_data if dp["path"] not in existing
        ]
        logger.info("Found %s data points to process", len(to_process))
        return to_process

    @task(trigger_rule="all_done")
    def get_matched(data_points_list):
        matched = []
        for dp in data_points_list:
            if dp.get("is_unmatched", False):
                continue
            matched.append(dp)
        return matched

    @task(trigger_rule="all_done")
    def get_unmatched(data_points_list):
        unmatched = []
        for dp in data_points_list:
            if dp.get("is_unmatched", False):
                unmatched.append(dp)
        return unmatched

    @task(trigger_rule="all_done")
    def build_data_points(data_points_data):
        from src.campaigns.directors import DataPointDirector
        directors = []
        logger.info("Building matched data points", data_points_data)
        for dp_data in data_points_data:
            director = DataPointDirector()
            logger.info("Building data point %s", dp_data["name"])
            director.construct(dp_data)
            pickled_data = pickle.dumps(director)
            encoded_data = base64.b64encode(pickled_data).decode('utf-8')
            directors.append(encoded_data)
        return directors

    @task(trigger_rule="all_done")
    def build_unmatched(unmatched_data_points):
        from src.campaigns.directors import UnmatchedDirector
        directors = []
        for unmatched_data in unmatched_data_points:
            director = UnmatchedDirector()
            director.construct(unmatched_data)
            pickled_data = pickle.dumps(director)
            encoded_data = base64.b64encode(pickled_data).decode('utf-8')
            directors.append(encoded_data)
        return directors

    @task(trigger_rule="all_done")
    def save_data_points(dp_directors):
        for dp_director in dp_directors:
            encoded_data = dp_director.encode('utf-8')
            pickled_data = base64.b64decode(encoded_data)
            director = pickle.loads(pickled_data)
            logger.info("Committing data point %s to DB", director._builder.instance.__dict__)
            director.commit()

    # Define task flow
    setup_django = SetupDjango(
        task_id="setup_django"
    )

    campaigns_to_scan = get_campaings_to_scan()

    scan_data_points = ScanFTPDirectory.partial(
        task_id="scan_campaigns",
        retries=3,
        retry_delay=timedelta(seconds=30)
    ).expand(
        folder_data=campaigns_to_scan
    )

    data_points_to_process = get_data_points_to_process.expand(
        dp_data=scan_data_points.output
    )

    splitted = match_patterns.partial(level='data_point').expand(
        file_data=data_points_to_process
    )

    matched = get_matched.expand(
        data_points_list=splitted
    )

    build_matched_dps = build_data_points.expand(
        data_points_data=matched
    )

    unmatched = get_unmatched.expand(
        data_points_list=splitted
    )

    build_unmatched_dps = build_unmatched.expand(
        unmatched_data_points=unmatched
    )

    commit_matched_dps = save_data_points.expand(
        dp_directors=build_matched_dps
    )

    commit_unmatched_dps = save_data_points.expand(
        dp_directors=build_unmatched_dps
    )

    setup_django >> campaigns_to_scan >> scan_data_points >> data_points_to_process

    data_points_to_process >> splitted >> unmatched >> build_unmatched_dps >> commit_unmatched_dps
    data_points_to_process >> splitted >> matched >> build_matched_dps >> commit_matched_dps


dag = process_data_points()

if __name__ == "__main__":
    dag.test()










































