# Standard imports
import logging
import pickle
import base64
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
from airflow.models.param import Param
# Django imports
from django.conf import settings
# Project imports
from resources.airflow.operators import (
    ScanFTPDirectory,
    SetupDjango
)


# Globals
logger = logging.getLogger(__name__)
campaign_param = "{{params.campaign_name}}"


@dag(
    dag_id="process_campaigns",
    schedule=None,
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=["campaigns"],
    params={
        "campaign_name": Param(
            description="Name of the campaign to process",
            default="HIDROLOGIA"
        )
    }

)
def process_campaigns():
    setup_django = SetupDjango(
        task_id="setup_django"
    )

    scan_hydro_campaigns = ScanFTPDirectory(
        task_id="scan_hydro_campaigns",
        folder_data={
            "path": settings.BASE_FTP_PATH + "/" + campaign_param,
            "is_dir": True,
        }
    )

    @task
    def get_campaigns_to_process(campaigns_data):
        from resources.campaigns.models import Campaign
        paths = [campaign_data["path"] for campaign_data in campaigns_data]
        existing = Campaign.objects.filter(path__in=paths).values_list(
            "path",
            flat=True
        )
        to_process = [
            cd for cd in campaigns_data if cd["path"] not in existing
        ]
        logger.info("Found %s campaigns to process", len(to_process))
        return to_process

    @task
    def build_campaign(campaign_data):
        from resources.campaigns.dags.builder import CampaignBuilder
        builder = CampaignBuilder(campaign_data)
        builder.build()
        if not builder.result:
            logger.info("Invalid data for campaign %s", campaign_data["name"])
            return None
        builder.build_parent(campaign_param)
        builder.build_metadata()
        builder.build_date()
        builder.build_external_id()
        builder.build_location()
        pickled_data = pickle.dumps(builder)
        encoded_data = base64.b64encode(pickled_data).decode('utf-8')
        return {"builder": encoded_data}

    @task
    def save_campaign(campaign_builder):
        encoded_data = campaign_builder['builder'].encode('utf-8')
        pickled_data = base64.b64decode(encoded_data)
        builder = pickle.loads(pickled_data)
        builder.save_to_db()
        logger.info("Saved campaign %s", builder.result["name"])

    campaigns_to_process = get_campaigns_to_process(
        scan_hydro_campaigns.output
    )

    build_campaigns = build_campaign.expand(
        campaign_data=campaigns_to_process
    )

    save_campaigns = save_campaign.expand(
        campaign_builder=build_campaigns
    )

    setup_django >> scan_hydro_campaigns >> campaigns_to_process
    campaigns_to_process >> build_campaigns >> save_campaigns


dag = process_campaigns()

if __name__ == "__main__":
    dag.test()
