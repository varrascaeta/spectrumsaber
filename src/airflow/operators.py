# Standard imports
import os
import sys
import logging
# Project imports
from src.utils import FTPClient
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
