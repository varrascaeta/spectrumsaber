"""Tests for process_measurements DAG."""

from unittest.mock import MagicMock, patch

import pytest
from airflow.models import DagBag


class TestProcessMeasurementsDag:
    """Test process_measurements DAG structure and tasks."""

    @pytest.fixture
    def dag(self):
        """Load the process_measurements DAG."""
        from src.airflow.dags.process_measurements import (
            dag as process_measurements_dag,
        )

        return process_measurements_dag

    def test_dag_loaded(self, dag_bag):
        """Test that the DAG is loaded without errors."""
        dag = dag_bag.get_dag("process_measurements")
        assert dag is not None
        assert len(dag_bag.import_errors) == 0

    def test_dag_structure(self, dag):
        """Test DAG has the correct structure."""
        assert dag.dag_id == "process_measurements"
        assert dag.catchup is False
        assert "data_points" in dag.tags

    def test_dag_params(self, dag):
        """Test DAG parameters are defined correctly."""
        params = dag.params
        assert "coverage_name" in params
        assert params["coverage_name"] == "HIDROLOGIA"

    def test_dag_tasks(self, dag):
        """Test that all expected tasks exist in the DAG."""
        expected_tasks = [
            "setup_django",
            "get_data_points_to_scan",
        ]
        task_ids = [task.task_id for task in dag.tasks]
        for expected_task in expected_tasks:
            assert expected_task in task_ids, f"Task {expected_task} not found"

    def test_dag_dependencies(self, dag):
        """Test task dependencies are correct."""
        setup_django = dag.get_task("setup_django")
        get_data_points = dag.get_task("get_data_points_to_scan")

        # Check that setup_django runs before get_data_points
        assert get_data_points in setup_django.downstream_list

    @patch("src.campaigns.models.DataPoint")
    def test_get_data_points_to_scan(self, mock_datapoint, dag):
        """Test get_data_points_to_scan task."""
        # Setup mock data points
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.values_list.return_value = [
            "/path/to/dp1",
            "/path/to/dp2",
        ]
        mock_datapoint.objects = mock_queryset

        # Get the task
        task = dag.get_task("get_data_points_to_scan")

        # Mock context
        with patch(
            "src.airflow.dags.process_measurements.get_current_context"
        ) as mock_context:
            mock_context.return_value = {
                "params": {"coverage_name": "TEST_COVERAGE"}
            }
            with patch(
                "src.airflow.dags.process_measurements.get_param_from_context"
            ) as mock_get_param:
                mock_get_param.return_value = "TEST_COVERAGE"

                result = task.python_callable()

                # Should return list of paths
                assert len(result) == 2
                assert "/path/to/dp1" in result
                assert "/path/to/dp2" in result

    @patch("src.airflow.dags.process_measurements.FTPClient")
    @patch(
        "src.airflow.dags.process_measurements.get_bottom_level_file_recursive"
    )
    def test_get_measurements(self, mock_get_files, mock_ftp_client, dag):
        """Test get_measurements task."""
        # Setup mocks
        mock_get_files.return_value = [
            {"path": "/Punto 1/measurement1.txt"},
            {"path": "/Punto 1/Datos Complementarios/complimentary.dat"},
            {"path": "/Punto 1/measurement2.txt"},
        ]

        mock_ftp_instance = MagicMock()
        mock_ftp_client.return_value.__enter__.return_value = mock_ftp_instance

        # Get the task
        task = dag.get_task("get_measurements")

        result = task.python_callable("/test/data_point")

        # Verify results
        assert "matched" in result
        assert "complimentary" in result
        assert len(result["matched"]) == 2
        assert len(result["complimentary"]) == 1

        # Check that parent is set
        for item in result["matched"]:
            assert item["parent"] == "/test/data_point"
            assert item["is_complimentary"] is False

        for item in result["complimentary"]:
            assert item["parent"] == "/test/data_point"
            assert item["is_complimentary"] is True

    @patch(
        "src.airflow.dags.process_measurements.get_bottom_level_file_recursive"
    )
    @patch("src.airflow.dags.process_measurements.FTPClient")
    def test_get_measurements_empty(
        self, mock_ftp_client, mock_get_files, dag
    ):
        """Test get_measurements with no files."""
        # Setup mocks
        mock_get_files.return_value = []

        mock_ftp_instance = MagicMock()
        mock_ftp_client.return_value.__enter__.return_value = mock_ftp_instance

        # Get the task
        task = dag.get_task("get_measurements")

        result = task.python_callable("/test/empty_data_point")

        # Verify results
        assert "matched" in result
        assert "complimentary" in result
        assert len(result["matched"]) == 0
        assert len(result["complimentary"]) == 0
