# Standard imports
import os
import signal
from datetime import UTC, datetime
from ftplib import FTP, error_perm
from unittest.mock import Mock, mock_open, patch

# Third-party imports
import pytest


# Project imports
from spectrumsaber.cfg import GRAPHQL_JWT_TOKEN
from spectrumsaber.client import (
    DIR_LIST_PATTERN,
    FTPClient,
    SpectrumSaberClient,
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


@pytest.fixture
def mock_requests():
    """Create a mock for requests module"""
    with patch("spectrumsaber.client.requests") as mock_req:
        yield mock_req


@pytest.fixture
def saber_client():
    """Create a SpectrumSaberClient instance"""
    return SpectrumSaberClient()


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


class TestSpectrumSaberClient:
    """Test SpectrumSaberClient class"""

    def test_saber_client_initialization(self, saber_client):
        """Test SpectrumSaberClient initializes with None tokens"""
        assert saber_client.__token__ == GRAPHQL_JWT_TOKEN
        assert saber_client.__refresh_token__ is None
        assert saber_client.user is None

    def test_get_headers_without_token(self, saber_client):
        """Test __get_headers__ returns basic headers without token"""
        saber_client.__token__ = None
        headers = saber_client.__get_headers__()
        assert headers == {"Content-Type": "application/json"}

    def test_get_headers_with_token(self, saber_client):
        """Test __get_headers__ includes JWT token when available"""
        saber_client.__token__ = "test_token_123"
        headers = saber_client.__get_headers__()
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "JWT test_token_123",
        }

    def test_query_success(self, saber_client, mock_requests):
        """Test query sends GraphQL request successfully"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"test": "success"}}
        mock_requests.post.return_value = mock_response

        query = "query { test }"
        variables = {"var1": "value1"}
        result = saber_client.query(query, variables)

        assert result == {"data": {"test": "success"}}
        mock_requests.post.assert_called_once_with(
            "http://localhost:8000/graphql",
            timeout=10,
            json={"query": query, "variables": variables},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"JWT {saber_client.__token__}",
            },
        )

    def test_query_without_variables(self, saber_client, mock_requests):
        """Test query works without variables"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"test": "success"}}
        mock_requests.post.return_value = mock_response

        query = "query { test }"
        result = saber_client.query(query)

        assert result == {"data": {"test": "success"}}
        called_payload = mock_requests.post.call_args[1]["json"]
        assert "variables" not in called_payload

    def test_query_with_unauthenticated_error_refreshes_token(
        self, saber_client, mock_requests
    ):
        """Test query refreshes token when unauthenticated"""
        saber_client.__token__ = "expired_token"
        saber_client.__refresh_token__ = "refresh_token_123"

        # First call returns unauthenticated error
        mock_response_1 = Mock()
        mock_response_1.json.return_value = {
            "errors": [{"message": "Unauthenticated user"}]
        }

        # Refresh token call
        mock_response_refresh = Mock()
        mock_response_refresh.json.return_value = {
            "data": {
                "refreshToken": {
                    "success": True,
                    "token": {"token": "new_token_456"},
                }
            }
        }

        # Retry call after refresh
        mock_response_2 = Mock()
        mock_response_2.json.return_value = {"data": {"test": "success"}}

        mock_requests.post.side_effect = [
            mock_response_1,
            mock_response_refresh,
            mock_response_2,
        ]

        query = "query { test }"
        result = saber_client.query(query)

        assert result == {"data": {"test": "success"}}
        assert saber_client.__token__ == "new_token_456"
        assert mock_requests.post.call_count == 3

    def test_refresh_auth_token_success(self, saber_client, mock_requests):
        """Test __refresh_auth_token__ refreshes token successfully"""
        saber_client.__refresh_token__ = "refresh_token_123"

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "refreshToken": {
                    "success": True,
                    "token": {"token": "new_token_456"},
                }
            }
        }
        mock_requests.post.return_value = mock_response

        result = saber_client.__refresh_auth_token__()

        assert result is True
        assert saber_client.__token__ == "new_token_456"

    def test_refresh_auth_token_failure(self, saber_client, mock_requests):
        """Test __refresh_auth_token__ handles failure"""
        saber_client.__refresh_token__ = "refresh_token_123"

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"refreshToken": {"success": False}},
            "errors": [{"message": "Invalid token"}],
        }
        mock_requests.post.return_value = mock_response

        result = saber_client.__refresh_auth_token__()

        assert result is False

    def test_refresh_auth_token_without_refresh_token(self, saber_client):
        """Test __refresh_auth_token__ fails without refresh token"""
        saber_client.__refresh_token__ = None

        result = saber_client.__refresh_auth_token__()

        assert result is False

    def test_login_success(self, saber_client, mock_requests):
        """Test login authenticates user successfully"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "tokenAuth": {
                    "success": True,
                    "token": {"token": "auth_token_123"},
                    "refreshToken": {"token": "refresh_token_456"},
                }
            }
        }
        mock_requests.post.return_value = mock_response

        saber_client.login("testuser", "testpassword")

        assert saber_client.__token__ == "auth_token_123"
        assert saber_client.__refresh_token__ == "refresh_token_456"

    def test_login_failure(self, saber_client, mock_requests):
        """Test login handles authentication failure"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"tokenAuth": {"success": False}},
            "errors": [{"message": "Invalid credentials"}],
        }
        mock_requests.post.return_value = mock_response

        saber_client.login("baduser", "badpassword")

        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None

    def test_login_handles_missing_tokenAuth(
        self, saber_client, mock_requests
    ):
        """Test login handles missing tokenAuth in response"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {}}
        mock_requests.post.return_value = mock_response
        saber_client.login("user", "pass")
        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None

    def test_login_handles_missing_token_and_refresh(
        self, saber_client, mock_requests
    ):
        """Test login handles missing token and refreshToken fields"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"tokenAuth": {"success": True}}
        }
        mock_requests.post.return_value = mock_response
        saber_client.login("user", "pass")
        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None

    def test_login_handles_errors_field(self, saber_client, mock_requests):
        """Test login logs error when errors field is present"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"tokenAuth": {"success": False}},
            "errors": [{"message": "Some error"}],
        }
        mock_requests.post.return_value = mock_response
        saber_client.login("user", "pass")
        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None

    def test_run_query_calls_query_method(self, saber_client):
        """Test run_query delegates to query method"""
        with patch.object(
            saber_client, "query", return_value={"data": {"test": "result"}}
        ) as mock_query:
            query_string = "query { test }"
            params = {"var1": "value1"}
            result = saber_client.run_query(query_string, params)

            mock_query.assert_called_once_with(query_string, params)
            assert result == {"data": {"test": "result"}}

    def test_run_query_without_params(self, saber_client):
        """Test run_query works without params"""
        with patch.object(
            saber_client, "query", return_value={"data": {"test": "result"}}
        ) as mock_query:
            query_string = "query { test }"
            result = saber_client.run_query(query_string)

            mock_query.assert_called_once_with(query_string, None)
            assert result == {"data": {"test": "result"}}

    def test_verify_token_success(self, saber_client, mock_requests):
        """Test __verify_token__ validates token successfully"""
        saber_client.__token__ = "valid_token_123"

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"me": {"id": "1", "username": "testuser"}}
        }
        mock_requests.post.return_value = mock_response

        result = saber_client.__verify_token__()

        assert result is True
        assert saber_client.user == "testuser"

    def test_verify_token_failure_with_errors(
        self, saber_client, mock_requests
    ):
        """Test __verify_token__ fails when errors returned"""
        saber_client.__token__ = "invalid_token"

        mock_response = Mock()
        mock_response.json.return_value = {
            "errors": [{"message": "Invalid token"}]
        }
        mock_requests.post.return_value = mock_response

        result = saber_client.__verify_token__()

        assert result is False

    def test_verify_token_failure_no_user_data(
        self, saber_client, mock_requests
    ):
        """Test __verify_token__ fails when no user data returned"""
        saber_client.__token__ = "token_123"

        mock_response = Mock()
        mock_response.json.return_value = {"data": {"me": None}}
        mock_requests.post.return_value = mock_response

        result = saber_client.__verify_token__()

        assert result is False

    def test_verify_token_handles_request_exception(self, saber_client):
        """Test __verify_token__ handles request exceptions"""
        import requests as real_requests

        saber_client.__token__ = "token_123"

        # Patch requests.post to raise exception
        with patch("spectrumsaber.client.requests.post") as mock_post:
            mock_post.side_effect = real_requests.RequestException(
                "Network error"
            )
            result = saber_client.__verify_token__()

        assert result is False

    def test_login_with_valid_env_token(self, saber_client, mock_requests):
        """Test login uses existing valid token from environment"""
        saber_client.__token__ = "env_token_123"

        # Mock verify_token to return True
        with patch.object(saber_client, "__verify_token__", return_value=True):
            saber_client.login("testuser", "testpassword")

        # Should not make any mutation request
        mock_requests.post.assert_not_called()
        assert saber_client.__token__ == "env_token_123"

    def test_login_with_invalid_env_token(self, saber_client, mock_requests):
        """Test login proceeds with credentials when env token is invalid"""
        saber_client.__token__ = "invalid_env_token"

        # Mock login response
        login_response = Mock()
        login_response.json.return_value = {
            "data": {
                "tokenAuth": {
                    "success": True,
                    "token": {"token": "new_token_123"},
                    "refreshToken": {"token": "refresh_token_456"},
                }
            }
        }

        mock_requests.post.return_value = login_response

        with patch.object(
            saber_client, "__verify_token__", return_value=False
        ):
            saber_client.login("testuser", "testpassword")

        assert saber_client.__token__ == "new_token_123"
        assert saber_client.__refresh_token__ == "refresh_token_456"
        assert saber_client.updated_token is True

    def test_logout_clears_tokens(self, saber_client):
        """Test logout clears all authentication data"""
        saber_client.__token__ = "token_123"
        saber_client.__refresh_token__ = "refresh_token_456"
        saber_client.user = "testuser"

        saber_client.logout()

        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None
        assert saber_client.user is None

    def test_is_authenticated_returns_true_with_token(self, saber_client):
        """Test is_authenticated returns True when token exists"""
        saber_client.__token__ = "token_123"
        assert saber_client.is_authenticated() is True

    def test_is_authenticated_returns_false_without_token(self, saber_client):
        """Test is_authenticated returns False without token"""
        saber_client.__token__ = None
        assert saber_client.is_authenticated() is False

    def test_get_token_returns_token(self, saber_client):
        """Test get_token returns current token"""
        saber_client.__token__ = "token_123"
        assert saber_client.get_token() == "token_123"

    def test_get_token_returns_none_when_not_authenticated(self, saber_client):
        """Test get_token returns None when not authenticated"""
        saber_client.__token__ = None
        assert saber_client.get_token() is None


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


class TestCLIClient:
    """Test CLIClient class"""

    @pytest.fixture
    def cli_client(self):
        """Create a CLIClient instance"""
        from spectrumsaber.client import CLIClient

        return CLIClient()

    @pytest.fixture
    def mock_console(self):
        """Create a mock Console"""
        with patch("spectrumsaber.client.Console") as mock_console_class:
            yield mock_console_class.return_value

    def test_cli_client_initialization(self, cli_client):
        """Test CLIClient initializes properly"""
        assert cli_client.saber_client is not None
        assert isinstance(cli_client.saber_client, SpectrumSaberClient)

    def test_cli_client_login_success(self, cli_client):
        """Test login returns True on success"""
        with (
            patch.object(cli_client.saber_client, "login"),
            patch.object(
                cli_client.saber_client, "is_authenticated", return_value=True
            ),
        ):
            result = cli_client.login("testuser", "testpass")
            assert result is True

    def test_cli_client_login_failure(self, cli_client):
        """Test login returns False on failure"""
        with (
            patch.object(cli_client.saber_client, "login"),
            patch.object(
                cli_client.saber_client, "is_authenticated", return_value=False
            ),
        ):
            result = cli_client.login("baduser", "badpass")
            assert result is False

    def test_cli_client_get_token(self, cli_client):
        """Test get_token delegates to saber_client"""
        with patch.object(
            cli_client.saber_client, "get_token", return_value="token_123"
        ):
            result = cli_client.get_token()
            assert result == "token_123"

    def test_cli_client_execute_query(self, cli_client):
        """Test execute_query delegates to saber_client"""
        expected_result = {"data": {"test": "result"}}
        with patch.object(
            cli_client.saber_client,
            "run_query",
            return_value=expected_result,
        ):
            result = cli_client.execute_query(
                "query { test }", {"var1": "value1"}
            )
            assert result == expected_result

    def test_cli_client_save_to_file(self, cli_client, tmp_path):
        """Test save_to_file writes JSON data"""
        import json

        data = {"test": "data", "value": 123}
        filepath = tmp_path / "test_output.json"

        cli_client.save_to_file(data, str(filepath))

        assert filepath.exists()
        with open(filepath, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        assert loaded_data == data


class TestInteractiveClient:
    """Test InteractiveClient class"""

    @pytest.fixture
    def interactive_client(self):
        """Create an InteractiveClient instance"""
        from spectrumsaber.client import InteractiveClient

        with (
            patch("spectrumsaber.client.FTPClient"),
            patch("spectrumsaber.client.SpectrumSaberClient"),
        ):
            return InteractiveClient()

    def test_interactive_client_initialization(self, interactive_client):
        """Test InteractiveClient initializes with clients"""
        assert interactive_client.ftp_client is not None
        assert interactive_client.saber_client is not None


class TestMainFunction:
    """Test main CLI entry point"""

    @patch("spectrumsaber.client.sys.argv", ["client.py", "--help"])
    def test_main_with_help_flag(self):
        """Test main shows help when --help is passed"""
        from spectrumsaber.client import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        # argparse exits with code 0 for --help
        assert exc_info.value.code == 0

    @patch("spectrumsaber.client.sys.argv", ["client.py", "--interactive"])
    @patch("spectrumsaber.client.RichInteractiveClient")
    def test_main_interactive_mode(self, mock_rich_client):
        """Test main runs interactive mode"""
        from spectrumsaber.client import main

        mock_instance = Mock()
        mock_rich_client.return_value = mock_instance

        main()

        mock_instance.run.assert_called_once()

    @patch(
        "spectrumsaber.client.sys.argv",
        [
            "client.py",
            "--username",
            "testuser",
            "--password",
            "testpass",
            "--query",
            "query { test }",
        ],
    )
    @patch("spectrumsaber.client.CLIClient")
    @patch("spectrumsaber.client.Console")
    def test_main_query_mode_success(self, mock_console, mock_cli_client):
        """Test main executes query in CLI mode"""
        from spectrumsaber.client import main

        mock_client = Mock()
        mock_client.saber_client.is_authenticated.return_value = False
        mock_client.login.return_value = True
        mock_client.execute_query.return_value = {"data": {"test": "result"}}
        mock_cli_client.return_value = mock_client

        main()

        mock_client.login.assert_called_once_with("testuser", "testpass")
        mock_client.execute_query.assert_called_once()

    @patch(
        "spectrumsaber.client.sys.argv",
        [
            "client.py",
            "--username",
            "testuser",
            "--password",
            "testpass",
            "--show-token",
        ],
    )
    @patch("spectrumsaber.client.CLIClient")
    @patch("spectrumsaber.client.Console")
    def test_main_show_token(self, mock_console, mock_cli_client):
        """Test main shows token"""
        from spectrumsaber.client import main

        mock_client = Mock()
        mock_client.saber_client.is_authenticated.return_value = False
        mock_client.login.return_value = True
        mock_client.get_token.return_value = "token_123"
        mock_cli_client.return_value = mock_client

        main()

        mock_client.get_token.assert_called_once()

    @patch("spectrumsaber.client.Console")
    def test_main_query_without_credentials_fails(self, mock_console):
        """Test main exits when query requires auth but no credentials"""
        from spectrumsaber.client import main

        with (
            patch(
                "spectrumsaber.client.sys.argv",
                ["client.py", "--query", "query { test }"],
            ),
            patch("spectrumsaber.client.CLIClient") as mock_cli_client,
            patch("spectrumsaber.client.sys.exit") as mock_exit,
        ):
            mock_client = Mock()
            mock_client.saber_client.is_authenticated.return_value = False
            mock_cli_client.return_value = mock_client

            main()

            mock_exit.assert_called_once_with(1)
