"""Tests for process_data_points DAG."""

from unittest.mock import MagicMock, patch

import pytest
from airflow.models import DagBag


class TestProcessDataPointsDag:
    """Test process_data_points DAG structure and tasks."""

    @pytest.fixture
    def dag(self):
        """Load the process_data_points DAG."""
        from src.airflow.dags.process_data_points import (
            dag as process_data_points_dag,
        )

        return process_data_points_dag

    def test_dag_loaded(self, dag_bag):
        """Test that the DAG is loaded without errors."""
        dag = dag_bag.get_dag("process_data_points")
        assert dag is not None
        assert len(dag_bag.import_errors) == 0

    def test_dag_structure(self, dag):
        """Test DAG has the correct structure."""
        assert dag.dag_id == "process_data_points"
        assert dag.catchup is False
        assert "data_points" in dag.tags

    def test_dag_params(self, dag):
        """Test DAG parameters are defined correctly."""
        params = dag.params
        assert "coverage_name" in params
        assert "force_reprocess" in params
        assert params["coverage_name"] == "HIDROLOGIA"
        assert params["force_reprocess"] is False

    def test_dag_tasks(self, dag):
        """Test that all expected tasks exist in the DAG."""
        expected_tasks = [
            "setup_django",
            "get_campaings_to_scan",
            "filter_non_empty",
        ]
        task_ids = [task.task_id for task in dag.tasks]
        for expected_task in expected_tasks:
            assert expected_task in task_ids, f"Task {expected_task} not found"

    def test_dag_dependencies(self, dag):
        """Test task dependencies are correct."""
        setup_django = dag.get_task("setup_django")
        get_campaigns = dag.get_task("get_campaings_to_scan")

        # Check that setup_django runs before get_campaigns
        assert get_campaigns in setup_django.downstream_list

    @patch("src.campaigns.models.Campaign")
    def test_get_campaigns_to_scan_no_force(self, mock_campaign, dag):
        """Test get_campaigns_to_scan without force_reprocess."""
        # Setup mock campaigns
        mock_campaign_obj1 = MagicMock()
        mock_campaign_obj1.path = "/test/campaign1"
        mock_campaign_obj2 = MagicMock()
        mock_campaign_obj2.path = "/test/campaign2"

        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.filter.return_value = [
            mock_campaign_obj1,
            mock_campaign_obj2,
        ]
        mock_campaign.objects = mock_queryset

        # Get the task
        task = dag.get_task("get_campaings_to_scan")

        # Mock context
        with patch(
            "src.airflow.dags.process_data_points.get_current_context"
        ) as mock_context:
            mock_context.return_value = {
                "params": {"coverage_name": "TEST", "force_reprocess": False}
            }
            with patch(
                "src.airflow.dags.process_data_points.get_param_from_context"
            ) as mock_get_param:
                mock_get_param.side_effect = ["TEST", False]

                result = task.python_callable()

                # Should return folder data for both campaigns
                assert len(result) == 2
                assert result[0]["path"] == "/test/campaign1"
                assert result[1]["path"] == "/test/campaign2"
                assert result[0]["is_dir"] is True

    @patch("src.campaigns.models.Campaign")
    def test_get_campaigns_to_scan_with_force(self, mock_campaign, dag):
        """Test get_campaigns_to_scan with force_reprocess."""
        # Setup mock campaigns
        mock_campaign_obj = MagicMock()
        mock_campaign_obj.path = "/test/campaign"

        mock_queryset = MagicMock()
        mock_queryset.filter.return_value = [mock_campaign_obj]
        mock_campaign.objects = mock_queryset

        task = dag.get_task("get_campaings_to_scan")

        with patch(
            "src.airflow.dags.process_data_points.get_current_context"
        ) as mock_context:
            mock_context.return_value = {
                "params": {"coverage_name": "TEST", "force_reprocess": True}
            }
            with patch(
                "src.airflow.dags.process_data_points.get_param_from_context"
            ) as mock_get_param:
                mock_get_param.side_effect = ["TEST", True]

                result = task.python_callable()

                # Should return all campaigns
                assert len(result) == 1
                assert result[0]["path"] == "/test/campaign"

    @patch("src.campaigns.models.DataPoint")
    def test_get_data_points_to_process_no_force(self, mock_datapoint, dag):
        """Test get_data_points_to_process without force_reprocess."""
        # Setup
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.values_list.return_value = [
            "/existing/dp"
        ]
        mock_datapoint.objects = mock_queryset

        dp_data = [
            {"path": "/existing/dp", "is_dir": False},
            {"path": "/new/dp", "is_dir": False},
        ]

        task = dag.get_task("get_data_points_to_process")

        with patch(
            "src.airflow.dags.process_data_points.get_current_context"
        ) as mock_context:
            mock_context.return_value = {"params": {"force_reprocess": False}}
            with patch(
                "src.airflow.dags.process_data_points.get_param_from_context"
            ) as mock_get_param:
                mock_get_param.return_value = False

                result = task.python_callable(dp_data)

                # Should return only the new data point
                assert len(result) == 1
                assert result[0]["path"] == "/new/dp"

    @patch("src.campaigns.models.DataPoint")
    def test_get_data_points_to_process_with_force(self, mock_datapoint, dag):
        """Test get_data_points_to_process with force_reprocess."""
        dp_data = [
            {"path": "/dp1", "is_dir": False},
            {"path": "/dp2", "is_dir": False},
        ]

        task = dag.get_task("get_data_points_to_process")

        with patch(
            "src.airflow.dags.process_data_points.get_current_context"
        ) as mock_context:
            mock_context.return_value = {"params": {"force_reprocess": True}}
            with patch(
                "src.airflow.dags.process_data_points.get_param_from_context"
            ) as mock_get_param:
                mock_get_param.return_value = True

                result = task.python_callable(dp_data)

                # Should return all data points
                assert len(result) == 2
