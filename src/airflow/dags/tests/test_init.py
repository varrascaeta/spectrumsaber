"""Tests for DAG __init__ module."""

import os
import pytest


def test_dags_init_module():
    """Test that the dags __init__ module can be imported."""
    import src.airflow.dags

    # Verify module exists
    assert src.airflow.dags is not None


def test_all_dags_importable():
    """Test that all DAG modules can be imported."""
    # Ensure settings is properly configured
    from django.conf import settings

    if (
        not hasattr(settings, "BASE_FTP_PATH")
        or settings.BASE_FTP_PATH is None
    ):
        settings.BASE_FTP_PATH = "/test/ftp"

    # Test process_campaigns
    from src.airflow.dags import process_campaigns

    assert process_campaigns.dag is not None

    # Test process_coverage
    from src.airflow.dags import process_coverage

    assert process_coverage.dag is not None

    # Test process_data_points
    from src.airflow.dags import process_data_points

    assert process_data_points.dag is not None

    # Test process_measurements
    from src.airflow.dags import process_measurements

    assert process_measurements.dag is not None


def test_dag_ids_unique():
    """Test that all DAG IDs are unique."""
    from src.airflow.dags import (
        process_campaigns,
        process_coverage,
        process_data_points,
        process_measurements,
    )

    dag_ids = [
        process_campaigns.dag.dag_id,
        process_coverage.dag.dag_id,
        process_data_points.dag.dag_id,
        process_measurements.dag.dag_id,
    ]

    # Check uniqueness
    assert len(dag_ids) == len(set(dag_ids)), "DAG IDs must be unique"


def test_all_dags_have_tags():
    """Test that all DAGs have tags defined."""
    from src.airflow.dags import (
        process_campaigns,
        process_coverage,
        process_data_points,
        process_measurements,
    )

    dags = [
        process_campaigns.dag,
        process_coverage.dag,
        process_data_points.dag,
        process_measurements.dag,
    ]

    for dag in dags:
        assert dag.tags is not None, f"DAG {dag.dag_id} should have tags"
        assert (
            len(dag.tags) > 0
        ), f"DAG {dag.dag_id} should have at least one tag"


def test_all_dags_have_start_date():
    """Test that all DAGs have a start date."""
    from src.airflow.dags import (
        process_campaigns,
        process_coverage,
        process_data_points,
        process_measurements,
    )

    dags = [
        process_campaigns.dag,
        process_coverage.dag,
        process_data_points.dag,
        process_measurements.dag,
    ]

    for dag in dags:
        assert (
            dag.start_date is not None
        ), f"DAG {dag.dag_id} should have a start date"
