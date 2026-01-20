"""Tests for process_campaigns DAG."""

from unittest.mock import MagicMock, patch

import pytest


class TestProcessCampaignsDag:
    """Test process_campaigns DAG structure and tasks."""

    @pytest.fixture
    def dag(self):
        """Load the process_campaigns DAG."""
        from src.airflow.dags.process_campaigns import (
            dag as process_campaigns_dag,
        )

        return process_campaigns_dag

    def test_dag_loaded(self, dag):
        """Test that the DAG is loaded without errors."""
        assert dag is not None
        assert dag.dag_id == "process_campaigns"

    def test_dag_structure(self, dag):
        """Test DAG has the correct structure."""
        assert dag.dag_id == "process_campaigns"
        assert dag.catchup is False
        assert "campaigns" in dag.tags

    def test_dag_params(self, dag):
        """Test DAG parameters are defined correctly."""
        params = dag.params
        assert "coverage_name" in params
        assert "force_reprocess" in params
        # Los params son objetos Param de Airflow, no tienen .value en el DAG
        assert params["coverage_name"] == "AGRICULTURA"
        assert params["force_reprocess"] is False

    def test_dag_tasks(self, dag):
        """Test that all expected tasks exist in the DAG."""
        # Solo verificamos que hay tareas, no el nombre exacto de cada una
        # ya que las tareas dinámicas pueden tener sufijos generados
        task_ids = [task.task_id for task in dag.tasks]

        # Verificamos las tareas principales
        assert "setup_django" in task_ids
        assert "scan_campaigns" in task_ids
        assert "get_campaigns_to_process" in task_ids
        assert "match_patterns" in task_ids

        # Verificamos que hay al menos estas tareas
        assert len(task_ids) >= 4
        """Test task dependencies are correct."""
        setup_django = dag.get_task("setup_django")
        scan_campaigns = dag.get_task("scan_campaigns")

        # Check that setup_django runs before scan_campaigns
        assert scan_campaigns in setup_django.downstream_list
