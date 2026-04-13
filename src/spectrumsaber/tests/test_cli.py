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
    def test_main_with_already_authenticated(self, mock_console, mock_cli_client):
        """Test main when client is already authenticated"""
        from spectrumsaber.client import main

        mock_client = Mock()
        mock_client.saber_client.is_authenticated.return_value = True
        mock_client.execute_query.return_value = {"data": {"test": "result"}}
        mock_cli_client.return_value = mock_client

        main()

        # Should not call login since already authenticated
        mock_client.login.assert_not_called()
        mock_client.execute_query.assert_called_once()

    @patch(
        "spectrumsaber.client.sys.argv",
        ["client.py"],
    )
    @patch("spectrumsaber.client.CLIClient")
    @patch("spectrumsaber.client.Console")
    def test_main_with_no_action(self, mock_console, mock_cli_client):
        """Test main prints help when no action is specified"""
        from spectrumsaber.client import main

        mock_client = Mock()
        mock_cli_client.return_value = mock_client

        with patch("spectrumsaber.cli._build_arg_parser") as mock_parser_builder:
            mock_parser = Mock()
            mock_parser_builder.return_value = mock_parser
            mock_parser.parse_args.return_value = Mock(
                query=None,
                query_file=None,
                show_token=False,
                interactive=False,
                text2gql=False,
            )

            main()

            # Should call print_help when no action
            mock_parser.print_help.assert_called_once()

    @patch(
        "spectrumsaber.client.sys.argv",
        [
            "client.py",
            "--username",
            "testuser",
            "--password",
            "testpass",
            "--query-file",
            "/tmp/query.gql",
        ],
    )
    @patch("spectrumsaber.client.CLIClient")
    @patch("spectrumsaber.client.Console")
    def test_main_with_query_file(self, mock_console, mock_cli_client, tmp_path):
        """Test main executes query from file"""
        from spectrumsaber.client import main

        # Create a temporary query file
        query_file = tmp_path / "query.gql"
        query_file.write_text("query { testQuery }")

        mock_client = Mock()
        mock_client.saber_client.is_authenticated.return_value = False
        mock_client.login.return_value = True
        mock_client.execute_query.return_value = {"data": {"test": "result"}}
        mock_cli_client.return_value = mock_client

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "query { testQuery }"
            
            main()

            mock_client.execute_query.assert_called_once()

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
            "--variables-file",
            "/tmp/vars.json",
        ],
    )
    @patch("spectrumsaber.client.CLIClient")
    @patch("spectrumsaber.client.Console")
    def test_main_with_variables_file(self, mock_console, mock_cli_client):
        """Test main loads variables from file"""
        from spectrumsaber.client import main
        import json

        mock_client = Mock()
        mock_client.saber_client.is_authenticated.return_value = False
        mock_client.login.return_value = True
        mock_client.execute_query.return_value = {"data": {"test": "result"}}
        mock_cli_client.return_value = mock_client

        with patch("builtins.open", create=True) as mock_open:
            mock_file = Mock()
            mock_file.__enter__ = Mock(return_value=mock_file)
            mock_file.__exit__ = Mock(return_value=False)
            mock_open.return_value = mock_file
            
            with patch("json.load", return_value={"var1": "value1"}):
                main()

                mock_client.execute_query.assert_called_once()
                call_args = mock_client.execute_query.call_args
                assert call_args[0][1] == {"var1": "value1"}

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
            "--output",
            "/tmp/output.json",
        ],
    )
    @patch("spectrumsaber.client.CLIClient")
    @patch("spectrumsaber.client.Console")
    def test_main_with_output_file(self, mock_console, mock_cli_client):
        """Test main saves result to output file"""
        from spectrumsaber.client import main

        mock_client = Mock()
        mock_client.saber_client.is_authenticated.return_value = False
        mock_client.login.return_value = True
        mock_client.execute_query.return_value = {"data": {"test": "result"}}
        mock_cli_client.return_value = mock_client

        main()

        mock_client.save_to_file.assert_called_once_with(
            {"data": {"test": "result"}}, "/tmp/output.json"
        )

    @patch("spectrumsaber.cli.sys.argv", ["spectrumsaber-t2gql"])
    @patch("spectrumsaber.cli._run_text2gql_repl")
    def test_main_text2gql_entry_point(self, mock_run_repl):
        """Test main_t2gql entry point"""
        from spectrumsaber.cli import main_t2gql

        main_t2gql()

        mock_run_repl.assert_called_once()

    @patch(
        "spectrumsaber.cli.sys.argv",
        [
            "spectrumsaber-t2gql",
            "--provider",
            "anthropic",
            "--api-key",
            "test-key",
        ],
    )
    @patch("spectrumsaber.cli._run_text2gql_repl")
    def test_main_text2gql_with_args(self, mock_run_repl):
        """Test main_t2gql with provider and api key arguments"""
        from spectrumsaber.cli import main_t2gql

        main_t2gql()

        mock_run_repl.assert_called_once()
        args = mock_run_repl.call_args[0][0]
        assert args.provider == "anthropic"
        assert args.api_key == "test-key"

    @patch("spectrumsaber.client.sys.argv", ["client.py", "--text2gql"])
    @patch("spectrumsaber.cli._run_text2gql_repl")
    def test_main_with_text2gql_flag(self, mock_run_repl):
        """Test main with --text2gql flag calls text2gql repl"""
        from spectrumsaber.client import main

        main()

        mock_run_repl.assert_called_once()
