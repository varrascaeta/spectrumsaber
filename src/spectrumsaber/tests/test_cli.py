# Standard imports
from unittest.mock import Mock, patch

# Third-party imports
import pytest

# Project imports
from spectrumsaber.client import SpectrumSaberClient


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
