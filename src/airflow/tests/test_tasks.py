"""Tests for airflow tasks."""

import base64
import pickle
from unittest.mock import MagicMock, Mock, patch

import pytest
from airflow.exceptions import AirflowSkipException

from src.airflow.tasks import (
    build_multiple,
    build_single,
    check_non_empty_dict,
    commit_director,
    commit_multiple,
    filter_non_empty,
    get_dict_result,
    match_patterns,
    process_expanded_by_class_group,
    process_multiple_by_class_group,
    recurse_complimentary_dirs,
)


# Picklable mock classes for testing
class MockDirector:
    """Picklable mock director for testing."""
    
    def __init__(self, name="TestInstance"):
        self.name = name
        
    def commit(self):
        mock_instance = type('MockInstance', (object,), {'name': self.name})()
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

    @patch("src.campaigns.models.PathRule.match_files")
    @patch("src.campaigns.models.ComplimentaryDataType.is_complimentary")
    def test_match_patterns_basic(self, mock_is_complimentary, mock_match_files):
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

    @patch("src.campaigns.models.PathRule.match_files")
    @patch("src.campaigns.models.ComplimentaryDataType.is_complimentary")
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
        assert result["complimentary"][0]["path"] == "/test/complimentary/data.txt"

    @patch("src.campaigns.models.PathRule.match_files")
    @patch("src.campaigns.models.ComplimentaryDataType.is_complimentary")
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

    @patch("src.campaigns.models.PathRule.match_files")
    @patch("src.campaigns.models.ComplimentaryDataType.is_complimentary")
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

    @patch("src.airflow.utils.get_bottom_level_file_recursive")
    @patch("spectrumsaber.client.FTPClient")
    def test_recurse_complimentary_dirs_with_files(
        self, mock_ftp_class, mock_get_bottom
    ):
        """Test with complimentary files (non-directories)."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value.__enter__ = MagicMock(return_value=mock_ftp)
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


    @patch("src.airflow.utils.get_bottom_level_file_recursive")
    @patch("spectrumsaber.client.FTPClient")
    def test_recurse_complimentary_dirs_logs_count(
        self, mock_ftp_class, mock_get_bottom, caplog
    ):
        """Test that final file count is logged."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp_class.return_value.__exit__ = MagicMock(return_value=None)

        complimentary_data = [
            {"path": "/comp/file1.txt", "is_dir": False},
            {"path": "/comp/file2.txt", "is_dir": False},
            {"path": "/comp/file3.txt", "is_dir": False},
        ]

        with caplog.at_level("INFO"):
            recurse_complimentary_dirs.function(complimentary_data)

        assert "After recursion, found 3 complimentary files" in caplog.text

    @patch("src.airflow.utils.get_bottom_level_file_recursive")
    @patch("spectrumsaber.client.FTPClient")
    def test_recurse_complimentary_dirs_empty_list(
        self, mock_ftp_class, mock_get_bottom
    ):
        """Test with empty complimentary data."""
        mock_ftp = MagicMock()
        mock_ftp_class.return_value.__enter__ = MagicMock(return_value=mock_ftp)
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


class TestCommitDirector:
    """Test commit_director task."""

    def test_commit_director_success(self, caplog):
        """Test successful director commit."""
        mock_director = MockDirector("TestInstance")

        # Encode the director
        pickled_data = pickle.dumps(mock_director)
        encoded_data = base64.b64encode(pickled_data).decode("utf-8")

        with caplog.at_level("INFO"):
            commit_director.function(encoded_data)

        assert "Saved TestInstance" in caplog.text

    def test_commit_director_decodes_correctly(self):
        """Test that commit_director correctly decodes data."""
        mock_director = MockDirector("TestName")

        pickled_data = pickle.dumps(mock_director)
        encoded_data = base64.b64encode(pickled_data).decode("utf-8")

        commit_director.function(encoded_data)

        # Test passes if no exception was raised
        assert True


class TestBuildSingle:
    """Test build_single task."""

    @patch("src.airflow.tasks.pickle.dumps")
    @patch("src.campaigns.directors.get_director_by_class_name")
    def test_build_single_success(self, mock_get_director, mock_pickle_dumps, caplog):
        """Test successful single build."""
        mock_director = MagicMock()
        mock_get_director.return_value = MagicMock(return_value=mock_director)
        mock_pickle_dumps.return_value = b"pickled_data"

        data = {"name": "TestData", "value": 123}

        with caplog.at_level("INFO"):
            result = build_single.function(data, "TestDirector")

        # Verify director was constructed
        mock_director.construct.assert_called_once_with(data)
        
        # Verify result is encoded
        assert isinstance(result, str)
        
        # Verify log message
        assert "Building TestData model" in caplog.text

        # Verify pickle was called
        mock_pickle_dumps.assert_called_once_with(mock_director)

    @patch("src.airflow.tasks.pickle.dumps")
    @patch("src.campaigns.directors.get_director_by_class_name")
    def test_build_single_different_director_class(self, mock_get_director, mock_pickle_dumps):
        """Test build_single with different director class."""
        mock_director = MagicMock()
        mock_get_director.return_value = MagicMock(return_value=mock_director)
        mock_pickle_dumps.return_value = b"pickled_data"

        data = {"name": "AnotherTest"}

        build_single.function(data, "AnotherDirector")

        mock_get_director.assert_called_once_with("AnotherDirector")

    @patch("src.airflow.tasks.pickle.dumps")
    @patch("src.campaigns.directors.get_director_by_class_name")
    def test_build_single_encoding(self, mock_get_director, mock_pickle_dumps):
        """Test that build_single properly encodes director."""
        mock_director = MagicMock()
        mock_get_director.return_value = MagicMock(return_value=mock_director)
        mock_pickle_dumps.return_value = b"test_pickled_data"

        data = {"name": "Test"}

        result = build_single.function(data, "Director")

        # Verify result is base64 encoded
        expected = base64.b64encode(b"test_pickled_data").decode("utf-8")
        assert result == expected


class TestBuildMultiple:
    """Test build_multiple task."""

    @patch("src.airflow.tasks.pickle.dumps")
    @patch("src.campaigns.directors.get_director_by_class_name")
    def test_build_multiple_success(self, mock_get_director, mock_pickle_dumps, caplog):
        """Test successful multiple build."""
        mock_director_class = MagicMock()
        mock_get_director.return_value = mock_director_class
        mock_pickle_dumps.return_value = b"pickled_data"

        data_list = [
            {"name": "Data1"},
            {"name": "Data2"},
            {"name": "Data3"},
        ]

        with caplog.at_level("INFO"):
            result = build_multiple.function(data_list, "TestDirector")

        # Verify we got 3 results
        assert len(result) == 3

        # Verify directors were created and constructed
        assert mock_director_class.call_count == 3
        
        # Verify each result is a string (encoded)
        for r in result:
            assert isinstance(r, str)

        # Verify log messages
        assert "Building Data1 model" in caplog.text
        assert "Building Data2 model" in caplog.text
        assert "Building Data3 model" in caplog.text

    @patch("src.campaigns.directors.get_director_by_class_name")
    def test_build_multiple_empty_list(self, mock_get_director):
        """Test build_multiple with empty list."""
        result = build_multiple.function([], "TestDirector")
        assert result == []

    @patch("src.airflow.tasks.pickle.dumps")
    @patch("src.campaigns.directors.get_director_by_class_name")
    def test_build_multiple_single_item(self, mock_get_director, mock_pickle_dumps):
        """Test build_multiple with single item."""
        mock_director_class = MagicMock()
        mock_get_director.return_value = mock_director_class
        mock_pickle_dumps.return_value = b"pickled_data"

        data_list = [{"name": "SingleData"}]

        result = build_multiple.function(data_list, "TestDirector")

        assert len(result) == 1
        assert mock_director_class.call_count == 1


class TestCommitMultiple:
    """Test commit_multiple task."""

    def test_commit_multiple_success(self, caplog):
        """Test successful multiple commit."""
        # Create mock directors
        mock_directors = [MockDirector(f"Instance{i}") for i in range(3)]

        # Encode directors
        encoded_list = []
        for director in mock_directors:
            pickled = pickle.dumps(director)
            encoded = base64.b64encode(pickled).decode("utf-8")
            encoded_list.append(encoded)

        with caplog.at_level("INFO"):
            commit_multiple.function(encoded_list)

        # Verify log messages
        assert "Saved Instance0" in caplog.text
        assert "Saved Instance1" in caplog.text
        assert "Saved Instance2" in caplog.text

    def test_commit_multiple_empty_list(self):
        """Test commit_multiple with empty list."""
        # Should not raise error
        commit_multiple.function([])

    def test_commit_multiple_single_item(self, caplog):
        """Test commit_multiple with single item."""
        mock_director = MockDirector("SingleInstance")
        pickled = pickle.dumps(mock_director)
        encoded = base64.b64encode(pickled).decode("utf-8")

        with caplog.at_level("INFO"):
            commit_multiple.function([encoded])

        assert "Saved SingleInstance" in caplog.text
