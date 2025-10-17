# Standard imports
import logging
import pandas as pd
# Django imports
from django.core.management.base import BaseCommand, CommandParser
# Project imports
from src.campaigns.models import PathRule
from src.logging_cfg import setup_logger
logger = setup_logger(__name__)


DEFAULT_PATH_RULES = [
    {
        "name": "Coverage",
        "order": 1,
        "pattern": r"^(?P<name>[A-Z]+)&",
        "level": "coverage",
    },
    {
        "name": "Campaign ID-YYYYMMDD-GEO",
        "order": 1,
        "pattern": r"^(?P<external_id>\d+)-(?P<date>\d{8})-(?P<metadata__geo_code>.+)$",
        "level": "campaign",
    },
    {
        "name": "Campaign ID-YYYY-MM-DD-GEO",
        "order": 2,
        "pattern": r"^(?P<external_id>\d+)-(?P<date>\d{4}-\d{2}-\d{2})-(?P<metadata__geo_code>.+)$",
        "level": "campaign",
    },
    {
        "name": "Campaign GEO-YYYY-Mes-DD-TYPE",
        "order": 3,
        "pattern": r"^(?P<metadata__geo_code>.+)-(?P<date>\d{2}-[a-zA-Z]{3}-\d{2})-(?P<metadata__geo_type>.+)$",
        "level": "campaign",
    },
    {
        "name": "Campaign GEO-YYYY-MM-DD-TYPE",
        "order": 4,
        "pattern": r"^(?P<metadata__geo_code>.+)-(?P<date>\d{2}-\d{2}-\d{2})-(?P<metadata__geo_type>.+)$",
        "level": "campaign",
    },
    {
        "name": "Campaign N.N-YYYYMMDD-GEO",
        "order": 4,
        "pattern": r"^(?P<id>\d{1}\.\d{1})-(?P<date>\d{8})-(?P<metadata__geo_code>.+)$",
        "level": "campaign",
    },
    {
        "name": "Data Point Punto NN",
        "order": 1,
        "pattern": r"^(?P<name>Punto \d{2})$",
        "level": "data_point",
    }
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("Initializing default path rules")
        for path_rule_dict in DEFAULT_PATH_RULES:
            obj, created = PathRule.objects.update_or_create(
                name=path_rule_dict["name"],
                defaults=path_rule_dict
            )
            if created:
                logger.info("Created path rule: %s", obj)
            else:
                logger.info("Path rule already exists: %s", obj)