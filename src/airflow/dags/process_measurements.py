# Standard imports
import logging
from datetime import datetime
import pickle
import base64
# Airflow imports
from airflow.decorators import dag, task, task_group
from airflow.models.param import Param
from airflow.operators.python import get_current_context
# Project imports
from spectrumsaber.client import FTPClient
from src.airflow.operators import SetupDjango
from src.airflow.utils import get_param_from_context, get_bottom_level_file_recursive
from src.airflow.tasks import (
    check_non_empty_dict,
    filter_non_empty,
    process_multiple_by_class_group,
    get_dict_result
)


# Globals
logger = logging.getLogger(__name__)


@dag(
    dag_id="process_measurements",
    schedule=None,
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=["data_points"],
    params={
        "coverage_name": Param(
            type="string",
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
        data_points_paths = DataPoint.objects.filter(
            campaign__coverage__name=coverage_name,
            scan_complete=False
        ).values_list(
            "path",
            flat=True
        )
        data_points_paths = list(data_points_paths)
        logger.info("Found %s data points to scan", len(data_points_paths))
        return data_points_paths

    @task(trigger_rule="all_done")
    def get_measurements(data_point_path: str):
        from src.campaigns.models import ComplimentaryDataType
        with FTPClient() as ftp_client:
            measurements = get_bottom_level_file_recursive(
                ftp_client,
                data_point_path,
            )
        logger.info("Found %s measurements in data point %s", len(measurements), data_point_path)
        complimentary = []
        matched = []

        for measurement in measurements:
            measurement["parent"] = data_point_path
            if ComplimentaryDataType.is_complimentary(measurement["path"]):
                measurement["is_complimentary"] = True
                complimentary.append(measurement)
            else:
                measurement["is_complimentary"] = False
                matched.append(measurement)
        logger.info(
            "Data point %s: Matched %s files, Complimentary %s files",
            data_point_path,
            len(matched),
            len(complimentary)
        )
        return {
            "matched": matched,
            "complimentary": complimentary
        }

    # Define task flow
    setup_django = SetupDjango(
        task_id="setup_django"
    )

    data_points_to_scan = get_data_points_to_scan()

    measurements = get_measurements.expand(
        data_point_path=data_points_to_scan
    )

    for key, director_class, recurse_dirs in [
        ("matched", "MeasurementDirector", False),
        ("complimentary", "ComplimentaryDirector", False)
    ]:
        check = check_non_empty_dict.partial(
            key=key
        ).expand(dict_data=measurements)

        process_task = process_multiple_by_class_group(
            f"process_{key}",
            recurse_dirs=recurse_dirs
        )

        process = process_task.partial(
            selector_key=key,
            director_class=director_class
        ).expand(file_data=check)

        measurements >> check >> process

    setup_django >> data_points_to_scan >> measurements


dag = process_measurements()


if __name__ == "__main__":
    run_conf = {
        "coverage_name": "HIDROLOGIA"
    }
    dag.test(run_conf=run_conf)

