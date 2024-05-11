# Standard imports
import os
import sys
import json
# Project imports
from dags.utils import FTPClient
# Airflow imports
from airflow.models.baseoperator import BaseOperator


class DjangoOperator(BaseOperator):
    def execute(self, *args, **kwargs):
        sys.path.append('./spectral-pymg/')  # TODO: Change this to env var
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service.settings")
        import django
        django.setup()


class FTPGetterOperator(BaseOperator):
    def __init__(self, parent_data, parent_keys, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.parent_data = parent_data
        self.parent_keys = parent_keys

    def execute(self, *args, **kwargs) -> list[dict]:
        credentials_path = os.getenv("FTP_CREDENTIALS_FILEPATH")
        if not credentials_path:
            raise ValueError("FTP_CREDENTIALS_FILEPATH not set")
        else:
            credentials = json.load(open(credentials_path))
        client = FTPClient(credentials=credentials)
        children_data = client.get_dir_data(self.parent_data["path"])
        for child in children_data:
            child["parent"] = {}
            for key in self.parent_keys:
                if key == "parent":
                    child["parent"] = self.parent_data["parent"]
                else:
                    child["parent"][key] = self.parent_data[key]
        return children_data
