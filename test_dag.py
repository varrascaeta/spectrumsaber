# Standard imports
import sys
import logging
# Airflow imports
from airflow.models import DagBag


# Globals
logger = logging.getLogger(__name__)


def test_dag(dag_id):
    logging.getLogger('airflow').setLevel(logging.ERROR)
    dag_bag = DagBag()
    dag = dag_bag.get_dag(dag_id)
    if not dag:
        logger.error(f"DAG {dag_id} not found")
        return
    logger.info(f"Testing DAG {dag_id}")
    dag.test()


if __name__ == "__main__":
    dag_id = sys.argv[1]
    dag_run_id = test_dag(dag_id)
