# Standard imports
import os
import signal
from datetime import UTC, datetime
from ftplib import FTP, error_perm
from unittest.mock import Mock, mock_open, patch

# Third-party imports
import pytest


# Project imports
from spectrumsaber.client import (
    DIR_LIST_PATTERN,
    FTPClient,
    TimeoutContext,
    TimeoutException,
)


@pytest.fixture
def mock_ftp_connection():
    """Create a mock FTP connection"""
    mock_conn = Mock(spec=FTP)
    mock_conn.login.return_value = "230 User logged in"
    mock_conn.cwd = Mock()
    mock_conn.dir = Mock()
    mock_conn.quit = Mock()
    return mock_conn


@pytest.fixture
def ftp_client(mock_ftp_connection):
    """Create an FTPClient instance with mocked connection"""
    with patch("spectrumsaber.client.FTP", return_value=mock_ftp_connection):
        client = FTPClient(
            ftp_user="test_user",
            ftp_password="test_password",
            ftp_host="test.ftp.host",
        )
        client.connection = mock_ftp_connection
        return client


class TestTimeoutException:
    """Test TimeoutException class"""

    def test_timeout_exception_creation(self):
        """Test TimeoutException can be created"""
        exc = TimeoutException("Test timeout")
        assert str(exc) == "Test timeout"
        assert isinstance(exc, Exception)

    def test_timeout_exception_can_be_raised(self):
        """Test TimeoutException can be raised and caught"""
        with pytest.raises(TimeoutException) as exc_info:
            raise TimeoutException("Timeout occurred")
        assert "Timeout occurred" in str(exc_info.value)


class TestTimeoutContext:
    """Test TimeoutContext class"""

    def test_timeout_context_initialization(self):
        """Test TimeoutContext initializes with timeout value"""
        ctx = TimeoutContext(timeout=10)
        assert ctx.timeout == 10

    @patch("spectrumsaber.client.signal.signal")
    @patch("spectrumsaber.client.signal.alarm")
    def test_timeout_context_enter_sets_alarm(self, mock_alarm, mock_signal):
        """Test __enter__ sets signal alarm"""
        ctx = TimeoutContext(timeout=15)
        ctx.__enter__()
        mock_signal.assert_called_once_with(signal.SIGALRM, ctx.handler)
        mock_alarm.assert_called_once_with(15)

    @patch("spectrumsaber.client.signal.alarm")
    def test_timeout_context_exit_cancels_alarm(self, mock_alarm):
        """Test __exit__ cancels the alarm"""
        ctx = TimeoutContext(timeout=10)
        ctx.__exit__(None, None, None)
        mock_alarm.assert_called_once_with(0)

    def test_timeout_context_handler_raises_exception(self):
        """Test handler raises TimeoutException"""
        ctx = TimeoutContext(timeout=10)
        with pytest.raises(TimeoutException) as exc_info:
            ctx.handler(None, None)
        assert "Timeout ocurred" in str(exc_info.value)

    @patch("spectrumsaber.client.signal.signal")
    @patch("spectrumsaber.client.signal.alarm")
    def test_timeout_context_as_context_manager(self, mock_alarm, mock_signal):
        """Test TimeoutContext works as context manager"""
        with TimeoutContext(timeout=5) as ctx:
            assert ctx.timeout == 5
        # Verify alarm was cancelled on exit
        assert mock_alarm.call_count == 2  # Once on enter, once on exit
        mock_alarm.assert_any_call(5)
        mock_alarm.assert_any_call(0)


class TestFTPClient:
    """Test FTPClient class"""

    def test_ftp_client_initialization_success(self):
        """Test FTPClient initializes with valid credentials"""
        client = FTPClient(
            ftp_user="user",
            ftp_password="pass",
            ftp_host="host.com",
        )
        assert client.username == "user"
        assert client.password == "pass"
        assert client.host == "host.com"
        assert client.connection is None

    def test_ftp_client_initialization_missing_host(self):
        """Test FTPClient raises ValueError when host is missing"""
        with pytest.raises(ValueError) as exc_info:
            FTPClient(ftp_user="user", ftp_password="pass", ftp_host="")
        assert "FTP_HOST not set" in str(exc_info.value)

    def test_ftp_client_initialization_missing_user(self):
        """Test FTPClient raises ValueError when user is missing"""
        with pytest.raises(ValueError) as exc_info:
            FTPClient(ftp_user="", ftp_password="pass", ftp_host="host.com")
        assert "FTP_USER not set" in str(exc_info.value)

    def test_ftp_client_initialization_missing_password(self):
        """Test FTPClient raises ValueError when password is missing"""
        with pytest.raises(ValueError) as exc_info:
            FTPClient(ftp_user="user", ftp_password="", ftp_host="host.com")
        assert "FTP_PASSWORD not set" in str(exc_info.value)

    @patch("spectrumsaber.client.FTP")
    @patch("spectrumsaber.client.TimeoutContext")
    def test_ftp_client_context_manager_enter(
        self, mock_timeout, mock_ftp_class
    ):
        """Test FTPClient __enter__ connects to FTP server"""
        mock_ftp = Mock(spec=FTP)
        mock_ftp.login.return_value = "230 User logged in"
        mock_ftp_class.return_value = mock_ftp
        mock_timeout.return_value.__enter__ = Mock(return_value=mock_timeout)
        mock_timeout.return_value.__exit__ = Mock(return_value=None)

        client = FTPClient(
            ftp_user="user", ftp_password="pass", ftp_host="host.com"
        )
        with client as c:
            assert c is client
            mock_ftp.login.assert_called_once_with("user", "pass")

    @patch("spectrumsaber.client.FTP")
    def test_ftp_client_context_manager_exit(self, mock_ftp_class):
        """Test FTPClient __exit__ quits connection"""
        mock_ftp = Mock(spec=FTP)
        mock_ftp.login.return_value = "230 User logged in"
        mock_ftp.quit = Mock()
        mock_ftp_class.return_value = mock_ftp

        client = FTPClient(
            ftp_user="user", ftp_password="pass", ftp_host="host.com"
        )
        client.connection = mock_ftp
        client.__exit__(None, None, None)
        mock_ftp.quit.assert_called_once()

    @patch("spectrumsaber.client.FTP")
    def test_ftp_client_connect(self, mock_ftp_class):
        """Test connect method establishes FTP connection"""
        mock_ftp = Mock(spec=FTP)
        mock_ftp.login.return_value = "230 User logged in"
        mock_ftp_class.return_value = mock_ftp

        client = FTPClient(
            ftp_user="user", ftp_password="pass", ftp_host="host.com"
        )
        client.connect()

        mock_ftp_class.assert_called_once_with("host.com", encoding="latin-1")
        mock_ftp.login.assert_called_once_with("user", "pass")
        assert client.connection == mock_ftp

    def test_ftp_client_connect_handles_error_perm(self):
        """Test connect handles FTP error_perm exception"""

        client = FTPClient(
            ftp_user="user", ftp_password="pass", ftp_host="host.com"
        )
        with patch(
            "spectrumsaber.client.FTP",
            side_effect=error_perm("530 Login incorrect"),
        ):
            with pytest.raises(error_perm):
                client.connect()

    def test_ftp_client_connect_handles_generic_exception(self):
        """Test connect handles generic exception"""
        from spectrumsaber.client import FTPClient

        client = FTPClient(
            ftp_user="user", ftp_password="pass", ftp_host="host.com"
        )
        with patch(
            "spectrumsaber.client.FTP",
            side_effect=Exception("Connection error"),
        ):
            with pytest.raises(Exception):
                client.connect()

    def test_ftp_client_level_up(self, ftp_client, mock_ftp_connection):
        """Test level_up changes directory to parent"""
        ftp_client.level_up()
        mock_ftp_connection.cwd.assert_called_once_with("..")

    def test_ftp_client_parse_line_with_directory(self, ftp_client):
        """Test parse_line with directory entry"""
        line = "11-12-25  02:30PM       <DIR>          test_dir"
        result = ftp_client.parse_line("/base/path", line)

        assert result["name"] == "test_dir"
        assert result["path"] == os.path.join("/base/path", "test_dir")
        assert result["is_dir"] is True
        assert isinstance(result["created_at"], datetime)
        assert result["created_at"].tzinfo == UTC

    def test_ftp_client_parse_line_with_file(self, ftp_client):
        """Test parse_line with file entry"""
        line = "10-15-24  09:45AM              1234 test_file.txt"
        result = ftp_client.parse_line("/base/path", line)

        assert result["name"] == "test_file.txt"
        assert result["path"] == os.path.join("/base/path", "test_file.txt")
        assert result["is_dir"] is False
        assert isinstance(result["created_at"], datetime)

    def test_ftp_client_parse_line_with_invalid_format(self, ftp_client):
        """Test parse_line with invalid line format"""
        line = "invalid line format"
        result = ftp_client.parse_line("/base/path", line)
        assert result == {}

    def test_ftp_client_get_dir_data_success(self, ftp_client):
        """Test get_dir_data retrieves and parses directory listing"""
        lines = [
            "11-12-25  02:30PM       <DIR>          dir1",
            "10-15-24  09:45AM              1234 file1.txt",
        ]

        def mock_dir(path, callback):
            for line in lines:
                callback(line)

        ftp_client.connection.dir = mock_dir

        result = ftp_client.get_dir_data("/test/path")

        assert len(result) == 2
        assert result[0]["name"] == "dir1"
        assert result[0]["is_dir"] is True
        assert result[1]["name"] == "file1.txt"
        assert result[1]["is_dir"] is False

    def test_ftp_client_get_dir_data_permission_error(self, ftp_client):
        """Test get_dir_data handles permission errors"""
        ftp_client.connection.dir = Mock(
            side_effect=error_perm("550 Permission denied")
        )

        with (
            patch("builtins.open", mock_open()) as mock_file,
            patch.object(ftp_client, "parse_line"),
        ):
            result = ftp_client.get_dir_data("/forbidden/path")

        assert result == []
        mock_file.assert_called_once_with(
            "permission_errors.txt", "a", encoding="utf-8"
        )

    def test_ftp_client_get_dir_data_generic_error(self, ftp_client):
        """Test get_dir_data handles generic errors"""
        ftp_client.connection.dir = Mock(
            side_effect=Exception("Connection lost")
        )

        with patch.object(ftp_client, "parse_line"):
            result = ftp_client.get_dir_data("/test/path")

        assert result == []

    def test_ftp_client_get_files_at_depth(self, ftp_client):
        """Test get_files_at_depth retrieves files at specified depth"""
        # Mock get_dir_data to return files and directories
        mock_files = [
            {
                "name": "dir1",
                "path": "/test/dir1",
                "is_dir": True,
                "created_at": datetime.now(UTC),
            },
            {
                "name": "file1.txt",
                "path": "/test/file1.txt",
                "is_dir": False,
                "created_at": datetime.now(UTC),
            },
        ]

        with patch.object(ftp_client, "get_dir_data", return_value=mock_files):
            result = ftp_client.get_files_at_depth("/test", max_depth=1)

        # Should return non-directory files
        assert len(result) >= 1

    def test_ftp_client_str_representation(self, ftp_client):
        """Test __str__ returns proper representation"""
        result = str(ftp_client)
        assert result == "FTP:test_user@test.ftp.host"


class TestDirListPattern:
    """Test DIR_LIST_PATTERN regex"""

    def test_dir_list_pattern_matches_directory(self):
        """Test pattern matches directory entry"""
        import re

        line = "11-12-25  02:30PM       <DIR>          test_directory"
        match = re.match(DIR_LIST_PATTERN, line)

        assert match is not None
        assert match.group(1) == "11-12-25"  # date
        assert match.group(2) == "02:30PM"  # time
        assert match.group(3) == "<DIR>"  # kind
        assert match.group(4) == "test_directory"  # filename

    def test_dir_list_pattern_matches_file(self):
        """Test pattern matches file entry"""
        import re

        line = "10-15-24  09:45AM              1234 test_file.txt"
        match = re.match(DIR_LIST_PATTERN, line)

        assert match is not None
        assert match.group(1) == "10-15-24"  # date
        assert match.group(2) == "09:45AM"  # time
        assert match.group(3) == "1234"  # size
        assert match.group(4) == "test_file.txt"  # filename

    def test_dir_list_pattern_does_not_match_invalid(self):
        """Test pattern does not match invalid format"""
        import re

        line = "invalid format line"
        match = re.match(DIR_LIST_PATTERN, line)

        assert match is None
