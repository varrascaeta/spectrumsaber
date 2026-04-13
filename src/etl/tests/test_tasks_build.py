"""Tests for airflow tasks - build and commit tasks."""

import base64
import pickle
from unittest.mock import MagicMock, patch

import pytest

from etl.tasks import (
    build_multiple,
    build_single,
    commit_director,
    commit_multiple,
)


# Picklable mock classes for testing
class MockDirector:
    """Picklable mock director for testing."""

    def __init__(self, name="TestInstance"):
        self.name = name

    def commit(self):
        mock_instance = type("MockInstance", (object,), {"name": self.name})()
        return mock_instance


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

    @patch("etl.tasks.pickle.dumps")
    @patch("server.campaigns.directors.get_director_by_class_name")
    def test_build_single_success(
        self, mock_get_director, mock_pickle_dumps, caplog
    ):
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

    @patch("etl.tasks.pickle.dumps")
    @patch("server.campaigns.directors.get_director_by_class_name")
    def test_build_single_different_director_class(
        self, mock_get_director, mock_pickle_dumps
    ):
        """Test build_single with different director class."""
        mock_director = MagicMock()
        mock_get_director.return_value = MagicMock(return_value=mock_director)
        mock_pickle_dumps.return_value = b"pickled_data"

        data = {"name": "AnotherTest"}

        build_single.function(data, "AnotherDirector")

        mock_get_director.assert_called_once_with("AnotherDirector")

    @patch("etl.tasks.pickle.dumps")
    @patch("server.campaigns.directors.get_director_by_class_name")
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

    @patch("etl.tasks.pickle.dumps")
    @patch("server.campaigns.directors.get_director_by_class_name")
    def test_build_multiple_success(
        self, mock_get_director, mock_pickle_dumps, caplog
    ):
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

    @patch("server.campaigns.directors.get_director_by_class_name")
    def test_build_multiple_empty_list(self, mock_get_director):
        """Test build_multiple with empty list."""
        result = build_multiple.function([], "TestDirector")
        assert result == []

    @patch("etl.tasks.pickle.dumps")
    @patch("server.campaigns.directors.get_director_by_class_name")
    def test_build_multiple_single_item(
        self, mock_get_director, mock_pickle_dumps
    ):
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
