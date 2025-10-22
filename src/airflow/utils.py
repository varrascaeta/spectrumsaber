# Standard imports
import logging
# Airflow imports
from airflow.utils.context import Context


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
