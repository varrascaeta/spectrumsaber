# Standard imports
import datetime
import logging
import os
import json
# Project imports
from resources.dags.utils import FTPClient
# Airflow imports
from airflow.decorators import dag, task


logger = logging.getLogger(__name__)


@dag(
    dag_id="ftp_file_scanner",
    schedule=None,
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    tags=["ftp_scanner"],
)
def ftp_file_scanner():
    @task
    def scan_files() -> FTPClient:
        credentials_filepath = os.getenv("FTP_CREDENTIALS_FILEPATH")
        if not credentials_filepath:
            raise ValueError("FTP_CREDENTIALS_FILEPATH not set")
        else:
            credentials = json.load(open(credentials_filepath))
            client = FTPClient(
                host=credentials["host"],
                username=credentials["username"],
                password=credentials["password"],
            )
        base_ftp_path = os.getenv("BASE_FTP_PATH")
        if not base_ftp_path:
            raise ValueError("BASE_FTP_PATH not set")
        files = client.get_files(base_ftp_path)
        return files

    @task
    def print_files(files: list[str]) -> None:
        for file in files:
            logger.info(file)

    files = scan_files()
    result = print_files(files)

    files >> result


dag = ftp_file_scanner()


if __name__ == "__main__":
    dag.test()
