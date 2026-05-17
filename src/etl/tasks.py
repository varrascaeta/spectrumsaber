"""
Reusable Airflow task functions for the SpectrumSaber ETL pipeline.

Contains a collection of ``@task``-decorated functions shared across all
four ingestion DAGs (process_coverage, process_campaigns,
process_data_points, process_measurements).

Key tasks:
    match_patterns              -- Classifies FTP file entries as matched,
                                   unmatched, or complimentary using PathRule
                                   and ComplimentaryDataType from the campaigns
                                   app.
    check_non_empty_dict        -- Skips the branch if a dict key is absent or
                                   empty (trigger_rule="all_done").
    get_dict_result             -- Extracts a single key from a dict result.
    recurse_complimentary_dirs  -- Walks complimentary FTP directories to
                                   collect all leaf files via FTPClient.
    build_single                -- Constructs a single domain object via a
                                   named Director class and serialises it with
                                   pickle+base64 for XCom transport.
    build_multiple             -- Same as build_single but for a list of items.
    commit_director             -- Deserialises a pickled Director and calls
                                   commit() to persist the record.
    commit_multiple             -- Batch version of commit_director.

Task-group factories:
    process_expanded_by_class_group  -- Returns an expanded task group that
        applies build_single + commit_director to each item in a list,
        optionally recursing into complimentary directories first.
    process_multiple_by_class_group  -- Returns a task group callable that applies
        get_dict_result + build_multiple + commit_multiple for a given
        selector key (batch, single group instance). With recurse_dirs=True,
        returns the inner process_multiple_with_recursion variant which inserts
        recurse_complimentary_dirs between get and build.
"""

# Standard imports
import base64
import logging
import pickle

# Airflow imports
from airflow.decorators import task, task_group
from airflow.exceptions import AirflowSkipException
from etl.utils import get_bottom_level_file_recursive

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
    from server.campaigns.models import ComplimentaryDataType, PathRule

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
    from server.campaigns.directors import get_director_by_class_name

    logger.info("Building %s model", data["name"])
    director = get_director_by_class_name(director_class)()
    director.construct(data)
    pickled_data = pickle.dumps(director)
    encoded_data = base64.b64encode(pickled_data).decode("utf-8")
    return encoded_data


@task(trigger_rule="all_done")
def build_multiple(data_list: list, director_class):
    from server.campaigns.directors import get_director_by_class_name

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
    """
    Fan-out task group factory using Airflow dynamic task mapping.

    Creates one task group instance per item in ``file_data`` via ``.expand()``,
    so N files produce N parallel task groups in the DAG graph. Each group runs
    ``build_single`` → ``commit_director`` on a single file dict.

    When ``recurse_dirs=True``, a ``recurse_complimentary_dirs`` step is
    prepended inside each task group instance, recursing into the item's FTP
    directory before building. Recursion is scoped per-item (not over the
    full list).

    Args:
        group_id: Task group ID used as the Airflow UI label.
        file_data: List of file dicts; each becomes one expanded task group.
        director_class: Name of the Director class passed to ``build_single``.
        recurse_dirs: If True, recurse into complimentary dirs before building.

    Returns:
        The result of the expanded task group (already invoked via ``.expand()``).
    """

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
    """
    Batch task group factory — processes all files in one task group instance.

    Returns a task group **callable** (not yet invoked). The returned group runs
    ``get_dict_result`` → ``build_multiple`` → ``commit_multiple`` over the
    entire file list in a single task group, using named task IDs derived from
    ``selector_key`` so multiple instances can coexist in the same DAG.

    When ``recurse_dirs=True``, returns the inner ``process_multiple_with_recursion``
    variant, which inserts ``recurse_complimentary_dirs`` between ``get_dict_result``
    and ``build_multiple``. Recursion operates on the full batch (not per-item).

    Contrast with ``process_expanded_by_class_group``: this factory produces a
    single task group regardless of list length, using ``build_multiple`` /
    ``commit_multiple`` instead of fan-out with ``build_single`` / ``commit_director``.

    Args:
        group_id: Task group ID used as the Airflow UI label.
        recurse_dirs: If True, return the recursion-aware variant of the group.

    Returns:
        A ``@task_group``-decorated callable that the caller must invoke with
        ``(file_data, selector_key, director_class)`` arguments.
    """

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
        """
        Batch task group with complimentary-dir recursion.

        Chain: ``get_dict_result`` → ``recurse_complimentary_dirs`` →
        ``build_multiple`` → ``commit_multiple``. Recursion walks FTP dirs
        for the full file list before building. Returned by
        ``process_multiple_by_class_group`` when ``recurse_dirs=True``.
        """
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
