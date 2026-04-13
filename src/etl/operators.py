"""
Custom Airflow operators for the SpectrumSaber ETL pipeline.

SetupDjango:      Initialises the Django ORM inside an Airflow task worker
                  so downstream tasks can use Django models directly.
ScanFTPDirectory: Connects to the CONAE FTP server via FTPClient and
                  returns the immediate children of a given directory.
"""

# Standard imports
import logging
import os
import sys

# Airflow imports
from airflow.models.baseoperator import BaseOperator

# Project imports
from spectrumsaber.client import FTPClient

# Globals
logger = logging.getLogger(__name__)


class SetupDjango(BaseOperator):
    def execute(self, *args, **kwargs):
        import django

        if "./spectrumsaber/" not in sys.path:
            sys.path.insert(0, "./spectrumsaber/")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
        django.setup()


class ScanFTPDirectory(BaseOperator):
    template_fields = ("folder_data",)

    def __init__(self, folder_data: dict, depth: int = 1, **kwargs):
        self.folder_data = folder_data
        self.depth = depth
        super().__init__(**kwargs)

    def execute(self, *args, **kwargs) -> list[dict]:
        path = self.folder_data["path"]
        is_dir = self.folder_data["is_dir"]
        if is_dir:
            with FTPClient() as client:
                logger.info("Scanning %s", path)
                children_data = client.get_dir_data(path)
                for cd in children_data:
                    cd["parent"] = path
            return children_data
