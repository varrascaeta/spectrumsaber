# Standard imports
import os
import sys
import logging
import json
# Project imports
from resources.utils import FTPClient, dynamic_import
# Airflow imports
from airflow.utils.context import Context
from airflow.models.baseoperator import BaseOperator
from airflow.models.xcom_arg import PlainXComArg, XComArg


# Globals
logger = logging.getLogger(__name__)


class DjangoOperator(BaseOperator):
    def pre_execute(self, *args, **kwargs):
        sys.path.append("./spectrumsaber/")  # TODO: Change this to env var
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service.settings")
        import django
        django.setup()


class GetObjectDataOperator(DjangoOperator):
    def __init__(self, model_path, obj_name: str, **kwargs):
        super().__init__(**kwargs)
        self.name = obj_name
        self.model_path = model_path

    def execute(self, context: Context) -> dict:
        module, model_name = self.model_path.rsplit(".", 1)
        model = dynamic_import(module, model_name)
        try:
            file_obj = model.objects.get(name=self.name)
            return {
                "id": file_obj.id,
                "path": file_obj.path,
            }
        except model.DoesNotExist:
            file_obj = None
            parent_key = model.get_parent_key()
            logger.info(
                "%s not found. Try to get %s first...",
                model_name, parent_key
            )
        return None


class CreateObjectOperator(DjangoOperator):
    def __init__(self, model_path, object_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.object_data = object_data
        self.model_path = model_path

    def get_fields(self) -> 'tuple[dict, dict]':
        defaults = {
            "ftp_created_at": self.object_data["created_at"],
        }
        search_fields = {
            "name": self.object_data["name"],
            "path": self.object_data["path"],
        }
        parent_id = self.object_data.get("parent", {}).get("id")
        if parent_id:
            parent_key = self.model.get_parent_key()
            search_fields[parent_key] = parent_id
        return search_fields, defaults

    def log_unmatched_object(self) -> None:
        logger.info(
            "Unmatched %s: %s", str(self.model), self.object_data["path"]
        )
        with open(f"unmatched_{str(self.model)}.txt", "a") as f:
            data = json.dumps(self.object_data, default=str)
            f.write(f"{data}\n")

    def execute(self, context: Context) -> None:
        module, model_name = self.model_path.rsplit(".", 1)
        self.model = dynamic_import(module, model_name)
        if self.model.matches_pattern(self.object_data["name"]):
            search_fields, defaults = self.get_fields()
            file_obj, created = self.model.objects.update_or_create(
                **search_fields,
                defaults=defaults,
            )
            logger.info(
                "%s object %s",
                "Created" if created else "Found", file_obj
            )
        else:
            self.log_unmatched_object()


class ProcessObjectsOperator(DjangoOperator):
    def __init__(self, creator_module: str, parent_data: XComArg, **kwargs):
        super().__init__(**kwargs)
        self.creator_module = creator_module
        self.parent_data = parent_data

    def get_ids_from_context(self, context: Context) -> list[dict]:
        parent_ids = []
        task_instance = context["ti"]
        task_parent_data = task_instance.xcom_pull(
            key=self.parent_data.key
        )
        if isinstance(task_parent_data, dict):
            parent_ids = [task_parent_data["id"]]
        else:
            parent_ids = [data["id"] for data in task_parent_data]
        return parent_ids

    def execute(self, *args, **kwargs) -> None:
        module, name = self.creator_module.rsplit(".", 1)
        self.creator = dynamic_import(module, name)
        parent_ids = self.get_ids_from_context(kwargs["context"])
        with FTPClient() as ftp_client:
            for idx, parent_id in enumerate(parent_ids):
                logger.info("="*80)
                creator_instance = self.creator(
                    parent_id=parent_id,
                    ftp_client=ftp_client
                )
                logger.info("Starting %s process", name)
                creator_instance.process()


class FTPGetterOperator(BaseOperator):
    def __init__(self, parent_data, parent_keys, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.parent_data = parent_data
        self.parent_keys = parent_keys

    def execute(self, *args, **kwargs) -> list[dict]:
        if isinstance(self.parent_data, PlainXComArg):
            task_instance = kwargs["context"]["ti"]
            self.parent_data = task_instance.xcom_pull(
                key=self.parent_data.key
            )
        with FTPClient() as client:
            children_data = client.get_dir_data(self.parent_data["path"])
        for child in children_data:
            child["parent"] = {}
            for key in self.parent_keys:
                if key == "parent":
                    child["parent"] = self.parent_data["parent"]
                else:
                    child["parent"][key] = self.parent_data[key]
        return children_data
