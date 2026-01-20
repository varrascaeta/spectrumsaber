# Standard imports
import logging

import requests

# Airflow imports
from airflow.utils.context import Context
from spectrumsaber.client import FTPClient
from src.airflow.gql_types import DagInfoType, DagParamType

logger = logging.getLogger(__name__)


def get_param_from_context(context: Context, param_name: str) -> str:
    dag_run = context.get("dag_run", None)
    if not dag_run:
        logger.warning("DAG run not found in context")
        param = None
    else:
        conf = dag_run.conf
        param = conf.get(param_name)
    logger.info("Param %s: %s", param_name, param)
    return param


def get_bottom_level_file_recursive(ftp_client: FTPClient, path: str) -> list:
    final_files = []
    children_data = ftp_client.get_dir_data(path)

    for child_data in children_data:
        if not child_data["is_dir"]:
            child_data["parent"] = path
            final_files.append(child_data)
        else:
            files = get_bottom_level_file_recursive(
                ftp_client, child_data["path"]
            )
            final_files.extend(files)
    return final_files


def trigger_dag(dag_id: str, conf: dict) -> str:
    from django.conf import settings

    logger.info("Triggering DAG %s with params %s", dag_id, conf)
    airflow_url = settings.AIRFLOW_WEBSERVER + f"/api/v1/dags/{dag_id}/dagRuns"
    payload = {"conf": conf}
    airflow_auth = (settings.AIRFLOW_USER, settings.AIRFLOW_PASSWORD)
    response = requests.post(
        airflow_url, timeout=10, auth=airflow_auth, json=payload
    )
    if response.status_code == 200:
        return (
            "DAG triggered successfully with run id: "
            + response.json().get("dag_run_id", "")
        )
    else:
        logger.error("Failed to trigger DAG %s: %s", dag_id, response.text)
        return "Failed to trigger DAG: " + response.text


def get_dags() -> list[DagInfoType] | None:
    from django.conf import settings

    airflow_url = settings.AIRFLOW_WEBSERVER + "/api/v1/dags"
    airflow_auth = (settings.AIRFLOW_USER, settings.AIRFLOW_PASSWORD)

    response = requests.get(airflow_url, timeout=10, auth=airflow_auth)
    if response.status_code == 200:
        logger.info("DAGs retrieved: %s", response.json())
        dags = []
        for dag in response.json().get("dags", []):
            dags.append(
                DagInfoType(
                    dag_id=dag.get("dag_id"),
                    dag_display_name=dag.get("dag_display_name"),
                    is_active=dag.get("is_active"),
                    is_paused=dag.get("is_paused"),
                    tags=[tag.get("name") for tag in dag.get("tags", [])],
                    description=dag.get("description"),
                    params=[],
                )
            )
        return dags
    return None


def get_dag_info(dag_id: str) -> DagInfoType | None:
    from django.conf import settings

    airflow_url = settings.AIRFLOW_WEBSERVER + f"/api/v1/dags/{dag_id}/details"
    airflow_auth = (settings.AIRFLOW_USER, settings.AIRFLOW_PASSWORD)

    response = requests.get(airflow_url, timeout=10, auth=airflow_auth)
    if response.status_code == 200:
        logger.info("DAG info retrieved: %s", response.json())
        return DagInfoType(
            dag_id=response.json().get("dag_id"),
            dag_display_name=response.json().get("dag_display_name"),
            is_active=response.json().get("is_active"),
            is_paused=response.json().get("is_paused"),
            tags=[tag.get("name") for tag in response.json().get("tags", [])],
            description=response.json().get("description"),
            params=[
                DagParamType(
                    name=param_name,
                    type=param_data.get("schema", {}).get("type"),
                    description=param_data.get("description"),
                )
                for param_name, param_data in response.json()
                .get("params", {})
                .items()
            ],
        )
    return None
