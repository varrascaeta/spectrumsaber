# Standard imports
import base64
import logging
import pickle

# Airflow imports
from airflow.decorators import task, task_group
from airflow.exceptions import AirflowSkipException
from src.airflow.utils import get_bottom_level_file_recursive

logger = logging.getLogger(__name__)


@task(trigger_rule="all_done")
def check_non_empty_dict(dict_data: dict, key: str):
    """
    Return the dict if it's non-empty; skip otherwise.
    """
    if not dict_data.get(key):
        raise AirflowSkipException(f"No data for key: {key}")
    return dict_data


@task
def match_patterns(file_data, level):
    from src.campaigns.models import ComplimentaryDataType, PathRule

    complimentary = []
    to_check = []
    for file in file_data:
        if ComplimentaryDataType.is_complimentary(file["path"]):
            file["is_complimentary"] = True
            complimentary.append(file)
        else:
            file["is_complimentary"] = False
            to_check.append(file)
    matched, unmatched = PathRule.match_files(to_check, level)
    logger.info(
        "Matched %s files, Unmatched %s files, Complimentary %s files",
        len(matched),
        len(unmatched),
        len(complimentary),
    )
    return {
        "matched": matched,
        "unmatched": unmatched,
        "complimentary": complimentary,
    }


@task(trigger_rule="all_done")
def get_dict_result(data: dict, key: str):
    """
    Extracts a value from a dictionary by key.
    """
    return data.get(key, [])


@task(trigger_rule="all_done")
def recurse_complimentary_dirs(complimentary_file_data):
    from spectrumsaber.client import FTPClient

    final_files = []
    with FTPClient() as ftp_client:
        for data in complimentary_file_data:
            if data["is_dir"]:
                files = get_bottom_level_file_recursive(
                    ftp_client, data["path"]
                )
                final_files.extend(files)
            else:
                final_files.append(data)
    logger.info(
        "After recursion, found %s complimentary files", len(final_files)
    )
    return final_files


@task
def filter_non_empty(files_groups):
    """
    Filters out empty lists from a list of lists.
    """
    if not files_groups:
        return []
    return [g for g in files_groups if g]


@task(trigger_rule="all_done")
def commit_director(director_data):
    encoded_data = director_data.encode("utf-8")
    pickled_data = base64.b64decode(encoded_data)
    director = pickle.loads(pickled_data)
    instance = director.commit()
    logger.info("Saved %s ", instance.name)


@task(trigger_rule="all_done")
def build_single(data: dict, director_class):
    from src.campaigns.directors import get_director_by_class_name

    logger.info("Building %s model", data["name"])
    director = get_director_by_class_name(director_class)()
    director.construct(data)
    pickled_data = pickle.dumps(director)
    encoded_data = base64.b64encode(pickled_data).decode("utf-8")
    return encoded_data


@task(trigger_rule="all_done")
def build_multiple(data_list: list, director_class):
    from src.campaigns.directors import get_director_by_class_name

    encoded_directors = []
    for data in data_list:
        logger.info("Building %s model", data["name"])
        director = get_director_by_class_name(director_class)()
        director.construct(data)
        pickled_data = pickle.dumps(director)
        encoded_data = base64.b64encode(pickled_data).decode("utf-8")
        encoded_directors.append(encoded_data)
    return encoded_directors


@task(trigger_rule="all_done")
def commit_multiple(directors_data_list: list):
    for director_data in directors_data_list:
        encoded_data = director_data.encode("utf-8")
        pickled_data = base64.b64decode(encoded_data)
        director = pickle.loads(pickled_data)
        instance = director.commit()
        logger.info("Saved %s ", instance.name)


def process_expanded_by_class_group(
    group_id: str,
    file_data: list[dict],
    director_class: str,
    recurse_dirs: bool = False,
):

    @task_group(group_id=group_id)
    def process_single_by_class(file_data: dict, director_class: str):
        build = build_single(file_data, director_class)
        commit_director(build)

    @task_group(group_id=group_id)
    def process_single_with_recursion(file_data: dict, director_class: str):
        recursed = recurse_complimentary_dirs(file_data)
        build = build_single(recursed, director_class)
        commit_director(build)

    if recurse_dirs:
        return process_single_with_recursion.partial(
            director_class=director_class
        ).expand(file_data=file_data)
    else:
        return process_single_by_class.partial(
            director_class=director_class
        ).expand(file_data=file_data)


def process_multiple_by_class_group(group_id: str, recurse_dirs: bool = False):

    @task_group(group_id=group_id)
    def process_multiple_by_class(
        file_data: dict, selector_key: str, director_class: str
    ):
        data_task = get_dict_result.override(
            task_id=f"get_result_{selector_key}"
        )
        build_task = build_multiple.override(task_id=f"build_{selector_key}")
        commit_task = commit_multiple.override(
            task_id=f"commit_{selector_key}"
        )

        data = data_task(file_data, selector_key)
        build = build_task(data, director_class)
        commit = commit_task(build)

        data >> build >> commit

    @task_group(group_id=group_id)
    def process_multiple_with_recursion(
        file_data: dict, selector_key: str, director_class: str
    ):
        data_task = get_dict_result.override(
            task_id=f"get_result_{selector_key}"
        )
        recursed_task = recurse_complimentary_dirs.override(
            task_id=f"recurse_complimentary_{selector_key}"
        )
        build_task = build_multiple.override(task_id=f"build_{selector_key}")
        commit_task = commit_multiple.override(
            task_id=f"commit_{selector_key}"
        )
        data = data_task(file_data, selector_key)
        recursed = recursed_task(data)
        build = build_task(recursed, director_class)
        commit = commit_task(build)

        data >> recursed >> build >> commit

    if recurse_dirs:
        return process_multiple_with_recursion
    else:
        return process_multiple_by_class
