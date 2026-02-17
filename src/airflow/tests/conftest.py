"""Pytest configuration for airflow tests."""

import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_django():
    """Setup Django for tests."""
    import django
    django.setup()


@pytest.fixture
def mock_ftp_client():
    """Mock FTPClient for tests."""
    mock_client = MagicMock()
    mock_client.get_dir_data.return_value = [
        {"path": "/test/path1", "is_dir": False, "name": "file1.txt"},
        {"path": "/test/path2", "is_dir": True, "name": "dir1"},
    ]
    return mock_client


@pytest.fixture
def mock_context():
    """Mock Airflow  context."""
    return {
        "dag_run": MagicMock(
            conf={"param1": "value1", "param2": "value2"}
        )
    }
