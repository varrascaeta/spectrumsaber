# Standard imports
import logging
import json
from datetime import datetime
# Airflow imports
from airflow.decorators import dag, task
from airflow import XComArg
# Django imports
from django.utils import timezone
# Project imports
from dags.operators import DjangoOperator, FTPGetterOperator


# Globals
logger = logging.getLogger(__name__)
current_task = 0
total_tasks = 0


@dag(
    dag_id="process_hydro_campaigns",
    schedule=None,
    start_date=datetime(2024, 4, 1),
    catchup=False,
    tags=["campaigns", "hydro"],
)
def process_hydro_campaigns() -> None:
    setup_django = DjangoOperator(task_id="setup_django")

    @task()
    def init_unmatched_file() -> None:
        run_date = timezone.now().strftime("%Y-%m-%d %H:%M:%s")
        with open("unmatched_campaigns_hydro.txt", "a") as f:
            f.write("="*80)
            f.write(f"\nUnmatched campaigns on {run_date}\n")

    @task()
    def get_coverage_data() -> dict:
        from resources.campaigns.models import Coverage
        try:
            coverage = Coverage.objects.get(name="HIDROLOGIA")
            return {"id": coverage.id, "path": coverage.path}
        except Coverage.DoesNotExist:
            logger.info(
                "Coverage not found. Try running process_coverage dag first..."
            )

    @task()
    def create_campaign(campaign_data: dict) -> dict:
        from resources.campaigns.models import Campaign
        parsed_attrs = Campaign.get_attributes_from_name(campaign_data["name"])
        if parsed_attrs:
            date = datetime.strptime(parsed_attrs["date_str"], "%Y%m%d").date()
            defaults = {
                "name": campaign_data["name"],
                "ftp_created_at": campaign_data["created_at"],
                "date": date,
                "external_id": parsed_attrs["external_id"],
            }
            campaign, created = Campaign.objects.get_or_create(
                path=campaign_data["path"],
                coverage_id=campaign_data["parent"]["id"],
                defaults=defaults
            )
            logger.info(f"{'Created' if created else 'Found'} {campaign}")
        else:
            logger.info(f"Skipping {campaign_data['name']}")
            with open("unmatched_campaigns_hydro.txt", "a") as f:
                data = json.dumps(campaign_data, default=str)
                f.write(f"{data}\n")

    # Define flow
    coverage_data = get_coverage_data()

    get_hydro_campaigns = FTPGetterOperator(
        task_id="get_hydro_campaings",
        parent_data=coverage_data,
        parent_keys=["id"]
    )

    init_file = init_unmatched_file()

    # Branch for each campaign
    create_campaigns = create_campaign.expand(
        campaign_data=XComArg(get_hydro_campaigns)
    )
    setup_django >> coverage_data >> get_hydro_campaigns >> init_file
    init_file >> create_campaigns


dag = process_hydro_campaigns()

if __name__ == "__main__":
    dag.test()
