"""Pytest configuration for DAG tests."""

import os
from unittest.mock import MagicMock, patch

import pytest
from airflow.models import DagBag


@pytest.fixture(scope="session", autouse=True)
def setup_django():
    """Setup Django for tests."""
    import django

    # Ensure BASE_FTP_PATH is set for testing
    os.environ.setdefault("BASE_FTP_PATH", "/test/ftp")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service.settings")
    django.setup()


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Mock Django settings for all tests."""
    from django.conf import settings

    if (
        not hasattr(settings, "BASE_FTP_PATH")
        or settings.BASE_FTP_PATH is None
    ):
        monkeypatch.setattr(settings, "BASE_FTP_PATH", "/test/ftp")


@pytest.fixture
def mock_ftp_client(monkeypatch):
    """Mock FTPClient for tests."""
    mock_client = MagicMock()
    mock_client.get_dir_data.return_value = [
        {"path": "/test/path1", "is_dir": False},
        {"path": "/test/path2", "is_dir": True},
    ]

    from spectrumsaber import client

    monkeypatch.setattr(client, "FTPClient", lambda: mock_client)
    return mock_client


@pytest.fixture
def dag_bag():
    """Get DagBag instance."""
    return DagBag(dag_folder="src/airflow/dags", include_examples=False)
