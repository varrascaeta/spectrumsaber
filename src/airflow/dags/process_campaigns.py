# Standard imports
import logging
import pickle
import base64
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import get_current_context
# Django imports
from django.conf import settings
# Project imports
from src.airflow.operators import (
    ScanFTPDirectory,
    SetupDjango
)
from src.airflow.tasks import (
    match_patterns,
    select_is_unmatched,
    build_unmatched,
    commit_to_db
)
from src.airflow.utils import get_param_from_context


# Globals
logger = logging.getLogger(__name__)
COVERAGE_PARAM = "{{ params.coverage_name }}"


@dag(
    dag_id="process_campaigns",
    schedule=None,
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=["campaigns"],
    params={
        "coverage_name": Param(
            description="Name of the coverage to process",
            default="AGRICULTURA"
        ),
        "force_reprocess": Param(
            description="Whether to force reprocessing of campaigns",
            default=False
        )
    }

)
def process_campaigns():
    @task
    def get_campaigns_to_process(campaigns_data):
        from src.campaigns.models import Campaign
        paths = [campaign_data["path"] for campaign_data in campaigns_data]
        context = get_current_context()
        force_reprocess = get_param_from_context(context, "force_reprocess")
        if force_reprocess:
            return campaigns_data
        existing = Campaign.objects.filter(
            scan_complete=True,
            path__in=paths
        ).values_list(
            "path",
            flat=True
        )
        to_process = [
            cd for cd in campaigns_data if cd["path"] not in existing
        ]
        logger.info("Found %s campaigns to process", len(to_process))
        return to_process

    @task
    def build_matched(matched_campaign_data):
        from src.campaigns.directors import CampaignDirector
        logger.info("Building campaign from data %s", matched_campaign_data)
        director = CampaignDirector()
        director.construct(matched_campaign_data)
        pickled_data = pickle.dumps(director)
        encoded_data = base64.b64encode(pickled_data).decode('utf-8')
        return {"director": encoded_data, "class_name": "Campaign"}

    # Define task flow

    setup_django = SetupDjango(
        task_id="setup_django"
    )

    scan_campaigns = ScanFTPDirectory(
        folder_data={
            "path": settings.BASE_FTP_PATH + "/" + COVERAGE_PARAM,
            "is_dir": True,
        },
        task_id="scan_campaigns",
    )

    campaigns_to_process = get_campaigns_to_process(
        scan_campaigns.output
    )

    apply_rules = match_patterns(
        file_data=campaigns_to_process,
        level="campaign"
    )

    unmatched_campaigns = select_is_unmatched(
        apply_rules,
        is_unmatched=True
    )

    matched_campaigns = select_is_unmatched(
        apply_rules,
        is_unmatched=False
    )

    build_campaigns_unmatched = build_unmatched.expand(
        unmatched_file_data=unmatched_campaigns
    )

    build_campaigns_matched = build_matched.expand(
        matched_campaign_data=matched_campaigns
    )

    save_matched_objects = commit_to_db.expand(
        director_data=build_campaigns_matched
    )

    save_unmatched_objects = commit_to_db.expand(
        director_data=build_campaigns_unmatched
    )

    setup_django >> scan_campaigns >> campaigns_to_process >> apply_rules    
    # Branch for unmatched and matched
    apply_rules >> unmatched_campaigns >> build_campaigns_unmatched >> save_unmatched_objects
    apply_rules >> matched_campaigns >> build_campaigns_matched >> save_matched_objects


dag = process_campaigns()

if __name__ == "__main__":
    dag.test()
