# Standard imports
import logging
import pickle
import base64
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task, task_group
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
    get_dict_result,
    match_patterns,
    check_non_empty_dict,
    process_expanded_by_class_group,

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
            type="string",
            description="Name of the coverage to process",
            default="AGRICULTURA"
        ),
        "force_reprocess": Param(
            type="boolean",
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

    splitted = match_patterns(
        campaigns_to_process,
        level="campaign"
    )

    check_matched = check_non_empty_dict(splitted, "matched")
    check_unmatched = check_non_empty_dict(splitted, "unmatched")
    check_complimentary = check_non_empty_dict(splitted, "complimentary")

    matched = get_dict_result(splitted, "matched")
    unmatched = get_dict_result(splitted, "unmatched")
    complimentary = get_dict_result(splitted, "complimentary")


    process_matched = process_expanded_by_class_group(
        "process_matched_campaigns",
        matched,
        "CampaignDirector",
    )
    process_unmatched = process_expanded_by_class_group(
        "process_unmatched_campaigns",
        unmatched,
        "UnmatchedDirector",
    )
    process_complimentary = process_expanded_by_class_group(
        "process_complimentary_campaigns",
        complimentary,
        "ComplimentaryDirector",
        recurse_dirs=True
    )

    setup_django >> scan_campaigns >> campaigns_to_process >> splitted
    splitted >> [
        check_matched >> process_matched,
        check_unmatched >> process_unmatched,
        check_complimentary >> process_complimentary
    ]

dag = process_campaigns()

if __name__ == "__main__":
    dag.test()
