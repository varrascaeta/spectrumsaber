# Standard imports
import logging
from datetime import datetime
import pickle
import base64
# Airflow imports
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import get_current_context
# Project imports
from src.airflow.operators import SetupDjango
from src.airflow.utils import get_param_from_context
from src.spectrumsaber.ftp_client import FTPClient


# Globals
logger = logging.getLogger(__name__)


def get_measurement_data_recursive(ftp_client: FTPClient, path: str) -> list:
    final_measurements = []
    children_data = ftp_client.get_dir_data(path)

    for child_data in children_data:
        if not child_data["is_dir"]:
            final_measurements.append(child_data)
        else:
            measurements = get_measurement_data_recursive(
                ftp_client,
                child_data["path"]
            )
            final_measurements.extend(measurements)
    return final_measurements


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
        with FTPClient() as ftp_client:
            measurements = get_measurement_data_recursive(
                ftp_client,
                data_point_path,
            )
        logger.info("Found %s measurements in data point %s", len(measurements), data_point_path)
        for measurement in measurements:
            measurement["parent"] = data_point_path

        return measurements

    @task(trigger_rule="all_done")
    def build_measurements(measurements_data):
        from src.campaigns.directors import MeasurementDirector
        directors = []
        logger.info("Building %s measurements", len(measurements_data))
        for m_data in measurements_data:
            director = MeasurementDirector()
            logger.info("Building measurement %s", m_data["name"])
            director.construct(m_data)
            pickled_data = pickle.dumps(director)
            encoded_data = base64.b64encode(pickled_data).decode('utf-8')
            directors.append(encoded_data)
        return directors

    @task(trigger_rule="all_done")
    def save_measurements(measurements_directors):
        for m_director in measurements_directors:
            encoded_data = m_director.encode('utf-8')
            pickled_data = base64.b64decode(encoded_data)
            director = pickle.loads(pickled_data)
            director.commit()

    # Define task flow
    setup_django = SetupDjango(
        task_id="setup_django"
    )

    data_points_to_scan = get_data_points_to_scan()

    process_measurements = get_measurements.expand(
        data_point_path=data_points_to_scan
    )

    build = build_measurements.expand(
        measurements_data=process_measurements
    )

    commit = save_measurements.expand(
        measurements_directors=build
    )


    setup_django >> data_points_to_scan >> process_measurements >> build >> commit


dag = process_measurements()

if __name__ == "__main__":
    run_conf = {
        "coverage_name": "HIDROLOGIA"
    }
    dag.test(run_conf=run_conf)

