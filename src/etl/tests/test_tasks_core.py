"""Tests for airflow tasks - core utility tasks."""

from unittest.mock import MagicMock, patch

import pytest
from airflow.exceptions import AirflowSkipException

from etl.tasks import (
    check_non_empty_dict,
    filter_non_empty,
    get_dict_result,
    match_patterns,
    recurse_complimentary_dirs,
)


# Picklable mock classes for testing
class MockDirector:
    """Picklable mock director for testing."""

    def __init__(self, name="TestInstance"):
        self.name = name

    def commit(self):
        mock_instance = type("MockInstance", (object,), {"name": self.name})()
        return mock_instance


class TestCheckNonEmptyDict:
    """Test check_non_empty_dict task."""

    def test_check_non_empty_dict_with_data(self):
        """Test with non-empty dict containing key."""
        data = {"key1": ["item1", "item2"], "key2": "value"}
        result = check_non_empty_dict.function(data, "key1")
        assert result == data

    def test_check_non_empty_dict_with_empty_value(self):
        """Test with empty value for key raises AirflowSkipException."""
        data = {"key1": [], "key2": "value"}

        with pytest.raises(AirflowSkipException) as exc_info:
            check_non_empty_dict.function(data, "key1")

        assert "No data for key: key1" in str(exc_info.value)

    def test_check_non_empty_dict_with_missing_key(self):
        """Test with missing key raises AirflowSkipException."""
        data = {"key1": "value"}

        with pytest.raises(AirflowSkipException) as exc_info:
            check_non_empty_dict.function(data, "key2")

        assert "No data for key: key2" in str(exc_info.value)

    def test_check_non_empty_dict_with_none_value(self):
        """Test with None value raises AirflowSkipException."""
        data = {"key1": None}

        with pytest.raises(AirflowSkipException):
            check_non_empty_dict.function(data, "key1")

    def test_check_non_empty_dict_with_false_value(self):
        """Test with False value raises AirflowSkipException."""
        data = {"key1": False}

        with pytest.raises(AirflowSkipException):
            check_non_empty_dict.function(data, "key1")

    def test_check_non_empty_dict_with_zero_value(self):
        """Test with zero value raises AirflowSkipException."""
        data = {"key1": 0}

        with pytest.raises(AirflowSkipException):
            check_non_empty_dict.function(data, "key1")

    def test_check_non_empty_dict_with_string_value(self):
        """Test with non-empty string value."""
        data = {"key1": "some value"}
        result = check_non_empty_dict.function(data, "key1")
        assert result == data

    def test_check_non_empty_dict_with_dict_value(self):
        """Test with non-empty dict value."""
        data = {"key1": {"nested": "value"}}
        result = check_non_empty_dict.function(data, "key1")
        assert result == data


class TestMatchPatterns:
    """Test match_patterns task."""

    @patch("server.campaigns.models.PathRule.match_files")
    @patch("server.campaigns.models.ComplimentaryDataType.is_complimentary")
    def test_match_patterns_basic(
        self, mock_is_complimentary, mock_match_files
    ):
        """Test basic pattern matching."""
        mock_is_complimentary.return_value = False
        mock_match_files.return_value = (
            [{"path": "/matched/file.txt"}],
            [{"path": "/unmatched/file.txt"}],
        )

        file_data = [
            {"path": "/test/file1.txt"},
            {"path": "/test/file2.txt"},
        ]

        result = match_patterns.function(file_data, level=1)

        assert "matched" in result
        assert "unmatched" in result
        assert "complimentary" in result
        assert len(result["matched"]) == 1
        assert len(result["unmatched"]) == 1
        assert len(result["complimentary"]) == 0

    @patch("server.campaigns.models.PathRule.match_files")
    @patch("server.campaigns.models.ComplimentaryDataType.is_complimentary")
    def test_match_patterns_with_complimentary(
        self, mock_is_complimentary, mock_match_files
    ):
        """Test pattern matching with complimentary files."""

        def is_comp_side_effect(path):
            return "complimentary" in path

        mock_is_complimentary.side_effect = is_comp_side_effect
        mock_match_files.return_value = (
            [{"path": "/matched/file.txt", "is_complimentary": False}],
            [],
        )

        file_data = [
            {"path": "/test/file.txt"},
            {"path": "/test/complimentary/data.txt"},
        ]

        result = match_patterns.function(file_data, level=1)

        assert len(result["complimentary"]) == 1
        assert result["complimentary"][0]["is_complimentary"] is True
        assert (
            result["complimentary"][0]["path"]
            == "/test/complimentary/data.txt"
        )

    @patch("server.campaigns.models.PathRule.match_files")
    @patch("server.campaigns.models.ComplimentaryDataType.is_complimentary")
    def test_match_patterns_logs_counts(
        self, mock_is_complimentary, mock_match_files, caplog
    ):
        """Test that file counts are logged."""
        mock_is_complimentary.return_value = False
        mock_match_files.return_value = (
            [{"path": f"/matched/file{i}.txt"} for i in range(5)],
            [{"path": f"/unmatched/file{i}.txt"} for i in range(3)],
        )

        file_data = [{"path": f"/test/file{i}.txt"} for i in range(8)]

        with caplog.at_level("INFO"):
            match_patterns.function(file_data, level=1)

        assert "Matched 5 files" in caplog.text
        assert "Unmatched 3 files" in caplog.text
        assert "Complimentary 0 files" in caplog.text

    @patch("server.campaigns.models.PathRule.match_files")
    @patch("server.campaigns.models.ComplimentaryDataType.is_complimentary")
    def test_match_patterns_empty_file_data(
        self, mock_is_complimentary, mock_match_files
    ):
        """Test with empty file data."""
        mock_match_files.return_value = ([], [])

        result = match_patterns.function([], level=1)

        assert result["matched"] == []
        assert result["unmatched"] == []
        assert result["complimentary"] == []


class TestGetDictResult:
    """Test get_dict_result task."""

    def test_get_dict_result_existing_key(self):
        """Test extracting existing key."""
        data = {"key1": [1, 2, 3], "key2": "value"}
        result = get_dict_result.function(data, "key1")
        assert result == [1, 2, 3]

    def test_get_dict_result_missing_key(self):
        """Test extracting missing key returns empty list."""
        data = {"key1": "value"}
        result = get_dict_result.function(data, "key2")
        assert result == []

    def test_get_dict_result_none_value(self):
        """Test extracting None value returns None."""
        data = {"key1": None}
        result = get_dict_result.function(data, "key1")
        assert result == None

    def test_get_dict_result_empty_dict(self):
        """Test with empty dictionary."""
        result = get_dict_result.function({}, "any_key")
        assert result == []

    def test_get_dict_result_different_types(self):
        """Test extracting different value types."""
        data = {
            "list": [1, 2, 3],
            "string": "hello",
            "dict": {"nested": "value"},
            "number": 42,
        }

        assert get_dict_result.function(data, "list") == [1, 2, 3]
        assert get_dict_result.function(data, "string") == "hello"
        assert get_dict_result.function(data, "dict") == {"nested": "value"}
        assert get_dict_result.function(data, "number") == 42


class TestRecurseComplimentaryDirs:
    """Test recurse_complimentary_dirs task."""

    @patch("etl.utils.get_bottom_level_file_recursive")
    @patch("spectrumsaber.client.FTPClient")
    def test_recurse_complimentary_dirs_with_files(
        self, mock_ftp_class, mock_get_bottom
    ):
        """Test with complimentary files (non-directories)."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value.__enter__ = MagicMock(
            return_value=mock_ftp
        )
        mock_ftp_class.return_value.__exit__ = MagicMock(return_value=None)

        complimentary_data = [
            {"path": "/comp/file1.txt", "is_dir": False},
            {"path": "/comp/file2.txt", "is_dir": False},
        ]

        result = recurse_complimentary_dirs.function(complimentary_data)

        assert len(result) == 2
        assert result[0]["path"] == "/comp/file1.txt"
        assert result[1]["path"] == "/comp/file2.txt"
        mock_get_bottom.assert_not_called()

    @patch("etl.utils.get_bottom_level_file_recursive")
    @patch("spectrumsaber.client.FTPClient")
    def test_recurse_complimentary_dirs_logs_count(
        self, mock_ftp_class, mock_get_bottom, caplog
    ):
        """Test that final file count is logged."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value.__enter__ = MagicMock(
            return_value=mock_ftp
        )
        mock_ftp_class.return_value.__exit__ = MagicMock(return_value=None)

        complimentary_data = [
            {"path": "/comp/file1.txt", "is_dir": False},
            {"path": "/comp/file2.txt", "is_dir": False},
            {"path": "/comp/file3.txt", "is_dir": False},
        ]

        with caplog.at_level("INFO"):
            recurse_complimentary_dirs.function(complimentary_data)

        assert "After recursion, found 3 complimentary files" in caplog.text

    @patch("etl.utils.get_bottom_level_file_recursive")
    @patch("spectrumsaber.client.FTPClient")
    def test_recurse_complimentary_dirs_empty_list(
        self, mock_ftp_class, mock_get_bottom
    ):
        """Test with empty complimentary data."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value.__enter__ = MagicMock(
            return_value=mock_ftp
        )
        mock_ftp_class.return_value.__exit__ = MagicMock(return_value=None)

        result = recurse_complimentary_dirs.function([])

        assert result == []


class TestFilterNonEmpty:
    """Test filter_non_empty task."""

    def test_filter_non_empty_with_all_non_empty(self):
        """Test filtering with all non-empty lists."""
        files_groups = [[1, 2], [3, 4], [5, 6]]
        result = filter_non_empty.function(files_groups)
        assert result == [[1, 2], [3, 4], [5, 6]]

    def test_filter_non_empty_with_some_empty(self):
        """Test filtering with some empty lists."""
        files_groups = [[1, 2], [], [3, 4], []]
        result = filter_non_empty.function(files_groups)
        assert result == [[1, 2], [3, 4]]

    def test_filter_non_empty_with_all_empty(self):
        """Test filtering with all empty lists."""
        files_groups = [[], [], []]
        result = filter_non_empty.function(files_groups)
        assert result == []

    def test_filter_non_empty_with_empty_input(self):
        """Test filtering with empty input."""
        result = filter_non_empty.function([])
        assert result == []

    def test_filter_non_empty_with_none_input(self):
        """Test filtering with None input."""
        result = filter_non_empty.function(None)
        assert result == []

    def test_filter_non_empty_with_nested_empty(self):
        """Test that only top-level empty lists are filtered."""
        files_groups = [[1, 2, []], [3, [4, []]], []]
        result = filter_non_empty.function(files_groups)
        assert result == [[1, 2, []], [3, [4, []]]]
