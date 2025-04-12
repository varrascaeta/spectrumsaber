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
from resources.airflow.operators import (
    ScanFTPDirectory,
    SetupDjango
)
from resources.utils import get_param_from_context


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
        )
    }

)
def process_data_points():
    @task
    def get_campaings_to_scan():
        from resources.campaigns.models import Campaign
        context = get_current_context()
        coverage_name = get_param_from_context(context, "coverage_name")
        campaigns = Campaign.objects.filter(
            coverage__name=coverage_name,
            scan_complete=False,
            is_unmatched=False
        )
        folder_data = [
            {"path": campaign.path, "is_dir": True}
            for campaign in campaigns
        ]
        logger.info("Found %s campaigns to scan", len(folder_data))
        return folder_data

    @task(trigger_rule="all_done")
    def get_data_points_to_process(dp_data):
        from resources.campaigns.models import DataPoint
        paths = [data["path"] for data in dp_data]
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
    def build_data_points(data_points_data):
        from resources.campaigns.dags.builder import DataPointBuilder
        builders = []
        for dp_data in data_points_data:
            builder = DataPointBuilder(dp_data)
            logger.info("Building data point %s", dp_data["name"])
            builder.build()
            if not builder.result:
                logger.info("Invalid data for data point %s", dp_data["name"])
                continue
            builder.build_parent()
            builder.build_metadata()
            builder.build_order()
            pickled_data = pickle.dumps(builder)
            encoded_data = base64.b64encode(pickled_data).decode('utf-8')
            builders.append(encoded_data)
        return builders

    @task(trigger_rule="all_done")
    def save_data_points(dp_builders):
        for dp_builder in dp_builders:
            encoded_data = dp_builder.encode('utf-8')
            pickled_data = base64.b64decode(encoded_data)
            builder = pickle.loads(pickled_data)
            builder.save_to_db()

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

    build_dps = build_data_points.expand(
        data_points_data=data_points_to_process
    )

    save_dps = save_data_points.expand(
        dp_builders=build_dps
    )

    setup_django >> campaigns_to_scan >> scan_data_points
    scan_data_points >> data_points_to_process >> build_dps >> save_dps


dag = process_data_points()

if __name__ == "__main__":
    dag.test()
