"""Tests for airflow operators."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from airflow.models.baseoperator import BaseOperator

from etl.operators import ScanFTPDirectory, SetupDjango


class TestSetupDjango:
    """Test SetupDjango operator."""

    def test_setup_django_inherits_from_base_operator(self):
        """Test that SetupDjango inherits from BaseOperator."""
        assert issubclass(SetupDjango, BaseOperator)

    def test_setup_django_execute(self):
        """Test SetupDjango execute method."""
        operator = SetupDjango(task_id="test_setup_django")

        # Execute should setup Django
        with patch("django.setup") as mock_django_setup:
            operator.execute()

            # Verify Django setup was called
            mock_django_setup.assert_called_once()

    def test_setup_django_execute_multiple_times(self):
        """Test SetupDjango can be executed multiple times."""
        operator = SetupDjango(task_id="test_setup_django")

        with patch("django.setup"):
            # Should not raise error when executed multiple times
            operator.execute()
            operator.execute()


class TestScanFTPDirectory:
    """Test ScanFTPDirectory operator."""

    def test_scan_ftp_directory_inherits_from_base_operator(self):
        """Test that ScanFTPDirectory inherits from BaseOperator."""
        assert issubclass(ScanFTPDirectory, BaseOperator)

    def test_scan_ftp_directory_initialization(self):
        """Test ScanFTPDirectory initialization."""
        folder_data = {"path": "/test/path", "is_dir": True}
        operator = ScanFTPDirectory(
            task_id="test_scan",
            folder_data=folder_data,
            depth=2,
        )

        assert operator.folder_data == folder_data
        assert operator.depth == 2
        assert operator.task_id == "test_scan"

    def test_scan_ftp_directory_initialization_default_depth(self):
        """Test ScanFTPDirectory initialization with default depth."""
        folder_data = {"path": "/test/path", "is_dir": True}
        operator = ScanFTPDirectory(
            task_id="test_scan",
            folder_data=folder_data,
        )

        assert operator.depth == 1

    def test_scan_ftp_directory_template_fields(self):
        """Test ScanFTPDirectory has correct template fields."""
        assert "folder_data" in ScanFTPDirectory.template_fields

    def test_scan_ftp_directory_execute_with_directory(self, mock_ftp_client):
        """Test ScanFTPDirectory execute with directory."""
        folder_data = {"path": "/test/path", "is_dir": True}
        operator = ScanFTPDirectory(
            task_id="test_scan",
            folder_data=folder_data,
        )

        mock_ftp_client.get_dir_data.return_value = [
            {
                "path": "/test/path/file1.txt",
                "is_dir": False,
                "name": "file1.txt",
            },
            {"path": "/test/path/dir1", "is_dir": True, "name": "dir1"},
        ]

        with patch("etl.operators.FTPClient") as mock_ftp_class:
            mock_ftp_class.return_value.__enter__ = MagicMock(
                return_value=mock_ftp_client
            )
            mock_ftp_class.return_value.__exit__ = MagicMock(return_value=None)

            result = operator.execute()

            # Verify FTPClient was called
            mock_ftp_client.get_dir_data.assert_called_once_with("/test/path")

            # Verify result contains children data with parent
            assert len(result) == 2
            assert result[0]["parent"] == "/test/path"
            assert result[1]["parent"] == "/test/path"

    def test_scan_ftp_directory_execute_with_file(self):
        """Test ScanFTPDirectory execute with file (not directory)."""
        folder_data = {"path": "/test/file.txt", "is_dir": False}
        operator = ScanFTPDirectory(
            task_id="test_scan",
            folder_data=folder_data,
        )

        with patch("etl.operators.FTPClient") as mock_ftp_class:
            result = operator.execute()

            # Should not call FTPClient for files
            mock_ftp_class.assert_not_called()
            assert result is None

    def test_scan_ftp_directory_execute_logs_path(
        self, mock_ftp_client, caplog
    ):
        """Test ScanFTPDirectory execute logs the path being scanned."""
        folder_data = {"path": "/test/scan/path", "is_dir": True}
        operator = ScanFTPDirectory(
            task_id="test_scan",
            folder_data=folder_data,
        )

        with patch("etl.operators.FTPClient") as mock_ftp_class:
            mock_ftp_class.return_value.__enter__ = MagicMock(
                return_value=mock_ftp_client
            )
            mock_ftp_class.return_value.__exit__ = MagicMock(return_value=None)

            with caplog.at_level("INFO"):
                operator.execute()

            assert "Scanning /test/scan/path" in caplog.text

    def test_scan_ftp_directory_execute_empty_directory(self, mock_ftp_client):
        """Test ScanFTPDirectory execute with empty directory."""
        folder_data = {"path": "/test/empty", "is_dir": True}
        operator = ScanFTPDirectory(
            task_id="test_scan",
            folder_data=folder_data,
        )

        mock_ftp_client.get_dir_data.return_value = []

        with patch("etl.operators.FTPClient") as mock_ftp_class:
            mock_ftp_class.return_value.__enter__ = MagicMock(
                return_value=mock_ftp_client
            )
            mock_ftp_class.return_value.__exit__ = MagicMock(return_value=None)

            result = operator.execute()

            assert result == []

    def test_scan_ftp_directory_execute_adds_parent_to_all_children(
        self, mock_ftp_client
    ):
        """Test that execute adds parent path to all children."""
        folder_data = {"path": "/parent/dir", "is_dir": True}
        operator = ScanFTPDirectory(
            task_id="test_scan",
            folder_data=folder_data,
        )

        mock_ftp_client.get_dir_data.return_value = [
            {"path": "/parent/dir/child1", "is_dir": False},
            {"path": "/parent/dir/child2", "is_dir": True},
            {"path": "/parent/dir/child3", "is_dir": False},
        ]

        with patch("etl.operators.FTPClient") as mock_ftp_class:
            mock_ftp_class.return_value.__enter__ = MagicMock(
                return_value=mock_ftp_client
            )
            mock_ftp_class.return_value.__exit__ = MagicMock(return_value=None)

            result = operator.execute()

            # Verify all children have parent field
            for child in result:
                assert child["parent"] == "/parent/dir"
