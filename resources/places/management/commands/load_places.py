# Standard imports
import logging
import pandas as pd
# Django imports
from django.core.management.base import BaseCommand, CommandParser
# Project imports
from resources.campaigns.models import Campaign
from resources.places.models import Country, District, Province


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.country, _ = Country.objects.get_or_create(
            name="Argentina",
            code="AR"
        )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--path", type=str, help="Filepath to load")

    def handle(self, *args, **options):
        path = options["path"]
        logger.info("Loading places from %s", path)
        places_data = pd.read_excel(path)
        for index, row in places_data.iterrows():
            logger.info("Processing row %s", index)
            self.parse_location(row)

    def parse_location(self, line) -> None:
        province, _ = Province.objects.get_or_create(
            name=line["Provincia"],
            country=self.country,
        )
        district, created = District.objects.get_or_create(
            name=line["Nombre"],
            province=province,
            code=line["Código"],
        )
        logger.info("District %s created: %s", district, created)
        campaigns = Campaign.objects.filter(metadata__geo_code=district.code)
        logger.info("Updating %s campaigns", campaigns.count())
        campaigns.update(district=district)
