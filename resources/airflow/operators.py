# Standard imports
import os
import sys
import logging
# Project imports
from resources.utils import FTPClient
# Airflow imports
from airflow.models.baseoperator import BaseOperator


# Globals
logger = logging.getLogger(__name__)


class SetupDjango(BaseOperator):
    def execute(self, *args, **kwargs):
        import django
        sys.path.append("./spectrumsaber/")  # TODO: Change this to env var
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service.settings")
        django.setup()


class ScanFTPDirectory(BaseOperator):
    def __init__(self, folder_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.path = folder_data["path"]
        self.is_dir = folder_data["is_dir"]

    def execute(self, *args, **kwargs) -> list[dict]:
        if self.is_dir:
            with FTPClient() as client:
                logger.info("Scanning %s", self.path)
                children_data = client.get_dir_data(self.path)
                for cd in children_data:
                    cd["parent"] = self.path
            return children_data
