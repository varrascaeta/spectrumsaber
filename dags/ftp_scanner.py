# Standard imports
import datetime
import json
import logging
import os
from collections.abc import Callable
# Project imports
from dags.operators import DjangoOperator
# Airflow imports
from airflow.decorators import dag, task

from dags.utils import FTPClient


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
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def get_children_data(parent_data: dict) -> list[dict]:
        path = parent_data["path"]
        credentials_path = os.getenv("FTP_CREDENTIALS_FILEPATH")
        if not credentials_path:
            raise ValueError("FTP_CREDENTIALS_FILEPATH not set")
        else:
            credentials = json.load(open(credentials_path))
        client = FTPClient(credentials=credentials)
        children_data = client.get_dir_data(path)
        for child in children_data:
            child["parent_id"] = parent_data.get("id", None)
        return children_data

    @task()
    def process_coverage(coverage_data: dict) -> int:
        from resources.campaigns.models import Coverage
        if Coverage.matches_pattern(coverage_data["name"]):
            coverage, created = Coverage.objects.get_or_create(
                name=coverage_data["name"],
                path=coverage_data["path"],
                created_at=coverage_data["created_at"],
            )
            logger.info(f"{'Created' if created else 'Found'} {coverage}")
            coverage_data["id"] = coverage.id
            return coverage_data

    @task()
    def process_campaign(campaign_data: list[dict]) -> None:
        from resources.campaigns.models import Campaign
        for data in campaign_data:
            parent_id = data["parent_id"]
            campaign, created = Campaign.objects.get_or_create(
                name=data["name"],
                path=data["path"],
                created_at=data["created_at"],
                coverage_id=parent_id,
            )
            logger.info(f"{'Created' if created else 'Found'} {campaign}")

    @task()
    def filter_files(data: list[dict], condition: Callable) -> list[dict]:
        return [d for d in data if condition(d)]

    # Define flow
    coverage_data = get_children_data(
        parent_data={
            'path': BASE_FTP_PATH
        }
    )
    # Branch for each coverage
    created_coverages_data = process_coverage.expand(
        coverage_data=coverage_data
    )
    # Filter only HIDRO for now
    filtered_coverages = filter_files(
        data=created_coverages_data,
        condition=lambda d: "HIDROLOGIA" in d['path']
    )
    # Branch for each campaign
    campaign_data = get_children_data.expand(parent_data=filtered_coverages)
    created_campaigns_data = process_campaign.expand(
        campaign_data=campaign_data
    )
    tasks = [
        setup_django,
        coverage_data,
        created_coverages_data,
        filtered_coverages,
        campaign_data,
        created_campaigns_data
    ]
    for i, task_id in enumerate(tasks[:-1]):
        task_id >> tasks[i+1]


dag = ftp_file_scanner()

if __name__ == "__main__":
    dag.test()
