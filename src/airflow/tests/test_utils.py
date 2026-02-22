"""Tests for airflow utils."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from src.airflow.utils import (
    get_bottom_level_file_recursive,
    get_param_from_context,
    trigger_dag,
)


class TestGetParamFromContext:
    """Test get_param_from_context function."""

    def test_get_param_from_context_success(self, mock_context):
        """Test getting parameter from context successfully."""
        result = get_param_from_context(mock_context, "param1")
        assert result == "value1"

    def test_get_param_from_context_different_param(self, mock_context):
        """Test getting different parameter from context."""
        result = get_param_from_context(mock_context, "param2")
        assert result == "value2"

    def test_get_param_from_context_missing_param(self, mock_context):
        """Test getting missing parameter returns None."""
        result = get_param_from_context(mock_context, "nonexistent")
        assert result is None

    def test_get_param_from_context_no_dag_run(self, caplog):
        """Test when dag_run is not in context."""
        context = {}
        
        with caplog.at_level("WARNING"):
            result = get_param_from_context(context, "param1")
        
        assert result is None
        assert "DAG run not found in context" in caplog.text

    def test_get_param_from_context_dag_run_none(self, caplog):
        """Test when dag_run is None."""
        context = {"dag_run": None}
        
        with caplog.at_level("WARNING"):
            result = get_param_from_context(context, "param1")
        
        assert result is None
        assert "DAG run not found in context" in caplog.text

    def test_get_param_from_context_logs_param(self, mock_context, caplog):
        """Test that parameter value is logged."""
        with caplog.at_level("INFO"):
            result = get_param_from_context(mock_context, "param1")
        
        assert "Param param1: value1" in caplog.text

    def test_get_param_from_context_empty_conf(self):
        """Test when conf is empty."""
        context = {"dag_run": MagicMock(conf={})}
        result = get_param_from_context(context, "param1")
        assert result is None

    def test_get_param_from_context_conf_none(self):
        """Test when conf is None."""
        context = {"dag_run": MagicMock(conf=None)}
        result = get_param_from_context(context, "param1")
        assert result is None

    def test_get_param_from_context_with_special_chars(self, mock_context):
        """Test parameter names with special characters."""
        mock_context["dag_run"].conf = {"param-with-dash": "value", "param_underscore": "value2"}
        result = get_param_from_context(mock_context, "param-with-dash")
        assert result == "value"

    def test_get_param_from_context_with_numeric_value(self):
        """Test extracting numeric parameter value."""
        context = {"dag_run": MagicMock(conf={"count": 42, "price": 99.99})}
        result = get_param_from_context(context, "count")
        assert result == 42

    def test_get_param_from_context_with_boolean_value(self):
        """Test extracting boolean parameter value."""
        context = {"dag_run": MagicMock(conf={"enabled": True, "disabled": False})}
        result = get_param_from_context(context, "enabled")
        assert result is True

    def test_get_param_from_context_with_list_value(self):
        """Test extracting list parameter value."""
        context = {"dag_run": MagicMock(conf={"items": [1, 2, 3]})}
        result = get_param_from_context(context, "items")
        assert result == [1, 2, 3]

    def test_get_param_from_context_with_dict_value(self):
        """Test extracting dict parameter value."""
        nested_dict = {"nested": {"key": "value"}}
        context = {"dag_run": MagicMock(conf={"data": nested_dict})}
        result = get_param_from_context(context, "data")
        assert result == nested_dict


class TestGetBottomLevelFileRecursive:
    """Test get_bottom_level_file_recursive function."""

    def test_get_bottom_level_file_recursive_only_files(self, mock_ftp_client):
        """Test with directory containing only files."""
        mock_ftp_client.get_dir_data.return_value = [
            {"path": "/test/file1.txt", "is_dir": False, "name": "file1.txt"},
            {"path": "/test/file2.txt", "is_dir": False, "name": "file2.txt"},
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert len(result) == 2
        assert result[0]["parent"] == "/test"
        assert result[1]["parent"] == "/test"
        assert result[0]["path"] == "/test/file1.txt"
        assert result[1]["path"] == "/test/file2.txt"

    def test_get_bottom_level_file_recursive_with_subdirs(self, mock_ftp_client):
        """Test with directory containing subdirectories."""
        # First call returns mix of files and dirs
        # Second call returns files from subdirectory
        mock_ftp_client.get_dir_data.side_effect = [
            [
                {"path": "/test/file1.txt", "is_dir": False, "name": "file1.txt"},
                {"path": "/test/subdir", "is_dir": True, "name": "subdir"},
            ],
            [
                {"path": "/test/subdir/file2.txt", "is_dir": False, "name": "file2.txt"},
            ],
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        # Should get files from both levels
        assert len(result) == 2
        assert any(f["path"] == "/test/file1.txt" for f in result)
        assert any(f["path"] == "/test/subdir/file2.txt" for f in result)

    def test_get_bottom_level_file_recursive_deeply_nested(self, mock_ftp_client):
        """Test with deeply nested directory structure."""
        mock_ftp_client.get_dir_data.side_effect = [
            [{"path": "/level1/level2", "is_dir": True, "name": "level2"}],
            [{"path": "/level1/level2/level3", "is_dir": True, "name": "level3"}],
            [{"path": "/level1/level2/level3/file.txt", "is_dir": False, "name": "file.txt"}],
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/level1")

        assert len(result) == 1
        assert result[0]["path"] == "/level1/level2/level3/file.txt"

    def test_get_bottom_level_file_recursive_empty_directory(self, mock_ftp_client):
        """Test with empty directory."""
        mock_ftp_client.get_dir_data.return_value = []

        result = get_bottom_level_file_recursive(mock_ftp_client, "/empty")

        assert result == []

    def test_get_bottom_level_file_recursive_only_directories(self, mock_ftp_client):
        """Test with directories that contain only other directories (no files)."""
        mock_ftp_client.get_dir_data.side_effect = [
            [{"path": "/test/dir1", "is_dir": True, "name": "dir1"}],
            [],  # dir1 is empty
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert result == []

    def test_get_bottom_level_file_recursive_mixed_structure(self, mock_ftp_client):
        """Test with complex mixed structure."""
        mock_ftp_client.get_dir_data.side_effect = [
            [
                {"path": "/root/file1.txt", "is_dir": False, "name": "file1.txt"},
                {"path": "/root/dir1", "is_dir": True, "name": "dir1"},
                {"path": "/root/file2.txt", "is_dir": False, "name": "file2.txt"},
                {"path": "/root/dir2", "is_dir": True, "name": "dir2"},
            ],
            [
                {"path": "/root/dir1/file3.txt", "is_dir": False, "name": "file3.txt"},
            ],
            [
                {"path": "/root/dir2/subdir", "is_dir": True, "name": "subdir"},
            ],
            [
                {"path": "/root/dir2/subdir/file4.txt", "is_dir": False, "name": "file4.txt"},
            ],
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/root")

        assert len(result) == 4
        paths = [f["path"] for f in result]
        assert "/root/file1.txt" in paths
        assert "/root/file2.txt" in paths
        assert "/root/dir1/file3.txt" in paths
        assert "/root/dir2/subdir/file4.txt" in paths

    def test_get_bottom_level_file_recursive_sets_parent(self, mock_ftp_client):
        """Test that parent field is set correctly for non-directory files."""
        mock_ftp_client.get_dir_data.return_value = [
            {"path": "/test/file.txt", "is_dir": False, "name": "file.txt"},
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test/parent")

        assert result[0]["parent"] == "/test/parent"

    def test_get_bottom_level_file_recursive_preserves_metadata(self, mock_ftp_client):
        """Test that file metadata is preserved during recursion."""
        mock_ftp_client.get_dir_data.return_value = [
            {
                "path": "/test/file.txt",
                "is_dir": False,
                "name": "file.txt",
                "size": 1024,
                "modified": "2024-01-01",
            },
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert result[0]["size"] == 1024
        assert result[0]["modified"] == "2024-01-01"
        assert result[0]["name"] == "file.txt"

    def test_get_bottom_level_file_recursive_multiple_levels_sets_correct_parent(
        self, mock_ftp_client
    ):
        """Test that parent is set correctly in multi-level recursion."""
        mock_ftp_client.get_dir_data.side_effect = [
            [{"path": "/root/dir1", "is_dir": True, "name": "dir1"}],
            [{"path": "/root/dir1/dir2", "is_dir": True, "name": "dir2"}],
            [{"path": "/root/dir1/dir2/file.txt", "is_dir": False, "name": "file.txt"}],
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/root")

        # Parent should be the immediate directory, not root
        assert result[0]["parent"] == "/root/dir1/dir2"

    def test_get_bottom_level_file_recursive_handles_many_files(self, mock_ftp_client):
        """Test with a large number of files."""
        many_files = [
            {"path": f"/test/file{i}.txt", "is_dir": False, "name": f"file{i}.txt"}
            for i in range(100)
        ]
        mock_ftp_client.get_dir_data.return_value = many_files

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert len(result) == 100
        assert all(f["parent"] == "/test" for f in result)

    def test_get_bottom_level_file_recursive_handles_special_chars_in_path(
        self, mock_ftp_client
    ):
        """Test with special characters in file paths."""
        mock_ftp_client.get_dir_data.return_value = [
            {
                "path": "/test/file-with-dash.txt",
                "is_dir": False,
                "name": "file-with-dash.txt",
            },
            {
                "path": "/test/file_with_underscore.txt",
                "is_dir": False,
                "name": "file_with_underscore.txt",
            },
            {"path": "/test/file.2024.txt", "is_dir": False, "name": "file.2024.txt"},
        ]

        result = get_bottom_level_file_recursive(mock_ftp_client, "/test")

        assert len(result) == 3
        paths = [f["path"] for f in result]
        assert "/test/file-with-dash.txt" in paths
        assert "/test/file_with_underscore.txt" in paths
        assert "/test/file.2024.txt" in paths


class TestTriggerDag:
    """Test trigger_dag function."""

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_success(self, mock_settings, mock_post):
        """Test successful DAG trigger."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"dag_run_id": "test_run_123"}
        mock_post.return_value = mock_response

        result = trigger_dag("test_dag", {"param": "value"})

        assert "DAG triggered successfully" in result
        assert "test_run_123" in result
        
        # Verify request was made correctly
        mock_post.assert_called_once_with(
            "http://localhost:8080/api/v1/dags/test_dag/dagRuns",
            timeout=10,
            auth=("admin", "admin"),
            json={"conf": {"param": "value"}},
        )

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_failure(self, mock_settings, mock_post, caplog):
        """Test DAG trigger failure."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request: DAG not found"
        mock_post.return_value = mock_response

        with caplog.at_level("ERROR"):
            result = trigger_dag("nonexistent_dag", {})

        assert "Failed to trigger DAG" in result
        assert "Bad Request: DAG not found" in result
        assert "Failed to trigger DAG nonexistent_dag" in caplog.text

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_logs_call(self, mock_settings, mock_post, caplog):
        """Test that DAG trigger is logged."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"dag_run_id": "test_run"}
        mock_post.return_value = mock_response

        with caplog.at_level("INFO"):
            trigger_dag("my_dag", {"key": "value"})

        assert "Triggering DAG my_dag" in caplog.text
        assert "{'key': 'value'}" in caplog.text

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_with_empty_conf(self, mock_settings, mock_post):
        """Test DAG trigger with empty configuration."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"dag_run_id": "run_456"}
        mock_post.return_value = mock_response

        result = trigger_dag("test_dag", {})

        assert "DAG triggered successfully" in result
        mock_post.assert_called_once()

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_without_run_id_in_response(self, mock_settings, mock_post):
        """Test DAG trigger when response doesn't contain dag_run_id."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # No dag_run_id
        mock_post.return_value = mock_response

        result = trigger_dag("test_dag", {})

        assert "DAG triggered successfully with run id:" in result

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_uses_correct_url(self, mock_settings, mock_post):
        """Test that trigger_dag constructs correct URL."""
        mock_settings.AIRFLOW_WEBSERVER = "http://airflow.example.com:8080"
        mock_settings.AIRFLOW_USER = "user"
        mock_settings.AIRFLOW_PASSWORD = "pass"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"dag_run_id": "run_id"}
        mock_post.return_value = mock_response

        trigger_dag("my_special_dag", {})

        expected_url = (
            "http://airflow.example.com:8080/api/v1/dags/my_special_dag/dagRuns"
        )
        actual_url = mock_post.call_args[0][0]
        assert actual_url == expected_url

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_uses_auth(self, mock_settings, mock_post):
        """Test that trigger_dag uses authentication."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "test_user"
        mock_settings.AIRFLOW_PASSWORD = "test_password"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        trigger_dag("test_dag", {})

        # Verify auth parameter
        assert mock_post.call_args[1]["auth"] == ("test_user", "test_password")

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_handles_connection_error(self, mock_settings, mock_post, caplog):
        """Test DAG trigger handles connection errors."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with pytest.raises(requests.exceptions.ConnectionError):
            trigger_dag("test_dag", {})

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_handles_timeout(self, mock_settings, mock_post):
        """Test DAG trigger handles timeout errors."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout):
            trigger_dag("test_dag", {})

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_with_401_status(self, mock_settings, mock_post, caplog):
        """Test DAG trigger with 401 Unauthorized."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "wrong_password"

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        with caplog.at_level("ERROR"):
            result = trigger_dag("test_dag", {})

        assert "Failed to trigger DAG" in result
        assert "Unauthorized" in result

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_with_404_status(self, mock_settings, mock_post, caplog):
        """Test DAG trigger with 404 Not Found."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "DAG not found"
        mock_post.return_value = mock_response

        with caplog.at_level("ERROR"):
            result = trigger_dag("nonexistent_dag", {})

        assert "Failed to trigger DAG" in result
        assert "DAG not found" in result

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_with_500_status(self, mock_settings, mock_post, caplog):
        """Test DAG trigger with 500 Internal Server Error."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with caplog.at_level("ERROR"):
            result = trigger_dag("test_dag", {})

        assert "Failed to trigger DAG" in result
        assert "Internal Server Error" in result

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_with_complex_conf(self, mock_settings, mock_post):
        """Test DAG trigger with complex nested configuration."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"dag_run_id": "complex_run"}
        mock_post.return_value = mock_response

        complex_conf = {
            "param1": "value1",
            "nested": {"key": "value", "list": [1, 2, 3]},
            "list_of_dicts": [{"a": 1}, {"b": 2}],
        }

        result = trigger_dag("test_dag", complex_conf)

        assert "DAG triggered successfully" in result
        assert "complex_run" in result
        # Verify the complex conf was passed correctly
        call_args = mock_post.call_args[1]["json"]
        assert call_args["conf"] == complex_conf

    @patch("src.airflow.utils.requests.post")
    @patch("django.conf.settings")
    def test_trigger_dag_verifies_timeout_parameter(self, mock_settings, mock_post):
        """Test that trigger_dag uses 10 second timeout."""
        mock_settings.AIRFLOW_WEBSERVER = "http://localhost:8080"
        mock_settings.AIRFLOW_USER = "admin"
        mock_settings.AIRFLOW_PASSWORD = "admin"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        trigger_dag("test_dag", {})

        # Verify timeout is set to 10 seconds
        assert mock_post.call_args[1]["timeout"] == 10
