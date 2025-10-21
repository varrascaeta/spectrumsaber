# Standard imports
import logging
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import get_current_context
# Project imports
from src.airflow.operators import SetupDjango
from src.utils import FTPClient, get_param_from_context


# Globals
logger = logging.getLogger(__name__)
coverage_param = "{{ params.coverage_name }}"


@dag(
    dag_id="process_measurements",
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
def process_measurements():
    @task
    def get_data_points_to_scan():
        from src.campaigns.models import DataPoint
        context = get_current_context()
        coverage_name = get_param_from_context(context, "coverage_name")
        data_points_ids = DataPoint.objects.filter(
            campaign__coverage__name=coverage_name,
            is_unmatched=False,
            scan_complete=False
        ).values_list(
            "id",
            flat=True
        )
        data_points_ids = list(data_points_ids)
        logger.info("Found %s data points to scan", len(data_points_ids))
        return data_points_ids

    @task(trigger_rule="all_done")
    def scan_and_process_measurements(data_point_id: int):
        from src.campaigns.measurement_creators import MeasurementCreator
        from src.campaigns.models import DataPoint
        with FTPClient() as ftp_client:
            creator = MeasurementCreator(data_point_id, ftp_client)
            creator.process()
        DataPoint.objects.filter(id=data_point_id).update(
            scan_complete=True
        )

    @task(trigger_rule="all_done")
    def mark_completed_campaigns():
        from src.campaigns.models import Campaign
        from src.campaigns.models import DataPoint
        context = get_current_context()
        coverage_name = get_param_from_context(context, "coverage_name")
        campaigns = Campaign.objects.filter(
            coverage__name=coverage_name,
            scan_complete=False,
            is_unmatched=False
        )
        to_update = []
        for campaign in campaigns:
            if not DataPoint.objects.filter(
                campaign=campaign,
                scan_complete=False
            ).exists():
                campaign.scan_complete = True
                to_update.append(campaign)

        Campaign.objects.bulk_update(
            to_update,
            ["scan_complete"]
        )

    # Define task flow
    setup_django = SetupDjango(
        task_id="setup_django"
    )

    data_points_to_scan = get_data_points_to_scan()

    process_measurements = scan_and_process_measurements.expand(
        data_point_id=data_points_to_scan
    )

    update_completed_campaigns = mark_completed_campaigns()

    setup_django >> data_points_to_scan >> process_measurements
    process_measurements >> update_completed_campaigns


dag = process_measurements()

if __name__ == "__main__":
    dag.test()
