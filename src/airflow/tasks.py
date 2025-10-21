# Standard imports
import logging
import pickle
import base64
# Airflow imports
from airflow.decorators import task


logger = logging.getLogger(__name__)

@task
def match_patterns(file_data, level):
    from src.campaigns.models import PathRule
    matched, unmatched = PathRule.match_files(
        file_data, level
    )
    logger.info("Matched %s files, Unmatched %s files", len(matched), len(unmatched))
    return matched + unmatched


@task
def select_is_unmatched(file_data, is_unmatched: bool):
    logger.info(file_data)
    selected = [
        cd for cd in file_data if cd.get("is_unmatched", False) == is_unmatched
    ]
    logger.info("Selected %s files with is_unmatched=%s", len(selected), is_unmatched)
    return selected


@task
def build_unmatched(unmatched_file_data):
    from src.campaigns.directors import UnmatchedDirector
    director = UnmatchedDirector()
    director.construct(unmatched_file_data)
    pickled_data = pickle.dumps(director)
    encoded_data = base64.b64encode(pickled_data).decode('utf-8')
    return {"director": encoded_data, "class_name": "UnmatchedFile"}


@task
def commit_to_db(director_data):
    encoded_data = director_data['director'].encode('utf-8')
    pickled_data = base64.b64decode(encoded_data)
    director = pickle.loads(pickled_data)
    instance = director.commit()
    logger.info("Saved %s %s", director_data['class_name'], instance.name)
