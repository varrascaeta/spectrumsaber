# Standard imports
import datetime
import logging
import os
import json
import sys
# Django imports
import django
# Project imports
from dags.utils import FTPClient
# Airflow imports
from airflow.decorators import dag, task


logger = logging.getLogger(__name__)
BASE_FTP_PATH = os.getenv("BASE_FTP_PATH")


@dag(
    dag_id="ftp_file_scanner",
    schedule=None,
    start_date=datetime.datetime(2021, 1, 1),
    catchup=False,
    tags=["ftp_scanner"],
)
def ftp_file_scanner():
    @task
    def get_ftp_credentials() -> dict:
        credentials_filepath = os.getenv("FTP_CREDENTIALS_FILEPATH")
        if not credentials_filepath:
            raise ValueError("FTP_CREDENTIALS_FILEPATH not set")
        else:
            return json.load(open(credentials_filepath))

    @task
    def setup_django() -> None:
        sys.path.append('./spectral-pymg/')  # TODO: Change this to env var
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service.settings")
        django.setup()

    @task
    def match_coverages(credentials: dict) -> list[dict]:
        from resources.campaigns.models import Coverage
        client = FTPClient(credentials=credentials)
        file_data = client.get_dir_data(BASE_FTP_PATH)
        matched_paths = []
        for data in file_data:
            if data.get("is_dir", False):
                if Coverage.matches_pattern(data["name"]):
                    matched_paths.append(data)
        return matched_paths

    @task
    def create_coverages(coverage_data: list[dict]) -> None:
        from resources.campaigns.models import Coverage
        for data in coverage_data:
            cover, created = Coverage.objects.get_or_create(
                name=data["name"],
                path=data["path"],
                created_at=data["created_at"],
            )
            if created:
                logger.info("Created %s", cover)
            else:
                logger.info("Already exists %s", cover)

    credentials = get_ftp_credentials()
    setup = setup_django()
    coverages = match_coverages(credentials)
    result = create_coverages(coverages)

    credentials >> setup >> coverages >> result


dag = ftp_file_scanner()


if __name__ == "__main__":
    dag.test()
