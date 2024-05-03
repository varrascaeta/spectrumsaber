# Standard imports
import os
import sys
# Airflow imports
from airflow.models.baseoperator import BaseOperator


class DjangoOperator(BaseOperator):
    def execute(self, *args, **kwargs):
        sys.path.append('./spectral-pymg/')  # TODO: Change this to env var
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service.settings")
        import django
        django.setup()
