"""
Utility helpers for the SpectrumSaber ETL pipeline.

Functions:
    get_param_from_context(context, param_name) -- Safely reads a DAG-run
        configuration parameter from the Airflow task context, returning
        None if the DAG run or its ``conf`` dict is absent.
    get_bottom_level_file_recursive(ftp_client, path) -- Recursively
        traverses an FTP directory tree via FTPClient, collecting all
        non-directory leaf entries and attaching a ``parent`` key to each.
    trigger_dag(dag_id, conf) -- Triggers a downstream Airflow DAG via the
        Airflow REST API, using connection settings from Django's settings
        module (AIRFLOW_WEBSERVER, AIRFLOW_USER, AIRFLOW_PASSWORD).
"""

# Standard imports
import logging

import requests

# Airflow imports
from airflow.utils.context import Context
from spectrumsaber.client import FTPClient

logger = logging.getLogger(__name__)


def get_param_from_context(context: Context, param_name: str) -> str:
    dag_run = context.get("dag_run", None)
    if not dag_run:
        logger.warning("DAG run not found in context")
        param = None
    else:
        conf = dag_run.conf
        if conf is None:
            param = None
        else:
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
