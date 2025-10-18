# Standard imports
import logging
import pandas as pd
# Django imports
from django.core.management.base import BaseCommand
# Project imports
from src.campaigns.models import PathRule
from src.logging_cfg import setup_logger
logger = setup_logger(__name__)


DEFAULT_PATH_RULES = [
    {
        'name': 'Coverage',
        'order': 1,
        'pattern': '^(?P<name>[A-Z]+)$',
        'date_format': None,
        'level': 'coverage'
    },
    # Campaign level patterns
    {
        'name': 'Campaign ID-YYYYMMDD-GEO',
        'order': 1,
        'pattern': '^(?P<external_id>\\d+)-(?P<date>\\d{8})-(?P<metadata__geo_code>.+)$',
        'date_format': None,
        'level': 'campaign'
    },
    {
        'name': 'Campaign ID-YYYY-MM-DD-GEO',
        'order': 2,
        'pattern': '^(?P<external_id>\\d+)-(?P<date>\\d{4}-\\d{2}-\\d{2})-(?P<metadata__geo_code>.+)$',
        'date_format': None,
        'level': 'campaign'
    },
    {
        'name': 'Campaign GEO-YYYY-Mes-DD-TYPE',
        'order': 3,
        'pattern': '^(?P<metadata__geo_code>.+)-(?P<date>\\d{2}-[a-zA-Z]{3}-\\d{2})-(?P<metadata__geo_type>.+)$',
        'date_format': '%d-%b-%y',
        'level': 'campaign'
    },
    {
        'name': 'Campaign GEO-YYYY-MM-DD-TYPE',
        'order': 4,
        'pattern': '^(?P<metadata__geo_code>.+)-(?P<date>\\d{2}-\\d{2}-\\d{2})-(?P<metadata__geo_type>.+)$',
        'date_format': None,
        'level': 'campaign'
    },
    {
        'name': 'Campaign N.N-YYYYMMDD-GEO',
        'order': 5,
        'pattern': '^(?P<id>\\d{1}\\.\\d{1})-(?P<date>\\d{8})-(?P<metadata__geo_code>.+)$',
        'date_format': None,
        'level': 'campaign'
    },
    # DataPoint level patterns
    {
        'name': 'Urbano LN-material',
        'order': 1,
        'pattern': '^L(?P<order>\\d+)-(?P<metadata__material>.+)$',
        'date_format': None,
        'level': 'data_point'
    },
    {
        'name': 'Data Point Punto NN',
        'order': 2,
        'pattern': '^Punto[\\W_]*(?P<order>\\d+)$',
        'date_format': None,
        'level': 'data_point'
    },
    {
        'name': 'Data Point Punto - NN - obs',
        'order': 3,
        'pattern': '^Punto[\\W_]*(?P<order>\\d+)-(?P<metadata__observacion>.+)$',
        'date_format': None,
        'level': 'data_point'
    },
    {
        'name': 'TIPOCONCENTRACIONN',
        'order': 4,
        'pattern': '^(?P<metadata__tipo_concentracion>[A-Z]+)(?P<order>\\d+)$',
        'date_format': None,
        'level': 'data_point'
    },
    {
        'name': 'TIPOAGUA',
        'order': 5,
        'pattern': '^(?P<metadata__tipo_agua>\\b(AT|AS)\\b)$',
        'date_format': None,
        'level': 'data_point'
    },
    {
        'name': 'TIPOCONCENTRACION-CN',
        'order': 6,
        'pattern': '^(?P<metadata__tipo_concentracion>[A-Z0-9]+)-[A-Z](?P<order>\\d+)$',
        'date_format': None,
        'level': 'data_point'
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