"""
SpectrumSaber CLI client module.

Provides all client classes and entry points for interacting with the
SpectrumSaber system from the command line or from other Python code.

Classes:
    FTPClient:             Connects to the CONAE FTP server, lists directory
                           contents, parses file metadata, and traverses the
                           directory tree to a given depth.
    SpectrumSaberClient:   JWT-authenticated GraphQL client; handles login,
                           token refresh, query execution, and exposes
                           text2gql() to create a Text2GQL translator.
    InteractiveClient:     Simple stdin/stdout interactive shell.
    RichInteractiveClient: Rich-enhanced interactive shell with menus, syntax
                           highlighting, and a built-in natural-language REPL.
    CLIClient:             Non-interactive client for scripting and automation.

Entry points:
    main()        -- ``spectrumsaber`` CLI command (interactive or scripted).
    main_t2gql()  -- ``spectrumsaber-t2gql`` dedicated text-to-GraphQL REPL.
"""

# Standard imports
import argparse
import json
import logging
import os
import re
import signal
import sys
from datetime import UTC, datetime
from ftplib import FTP, error_perm
from pathlib import Path

# Third party imports
import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

# Project imports
from spectrumsaber.cfg import (
    FTP_HOST,
    FTP_PASSWORD,
    FTP_USER,
    GRAPHQL_ENDPOINT,
    GRAPHQL_JWT_TOKEN,
)

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)
DIR_LIST_PATTERN = (
    r"^(\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?:AM|PM))\s+" r"(<DIR>|\d+)\s+(.+)$"
)
DATE_FORMAT = "%m-%d-%y"
TIME_FORMAT = "%I:%M%p"


# Class definitions
class TimeoutException(Exception):
    pass


class TimeoutContext:
    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    def __enter__(self):
        logger.info("Setting timeout to %s seconds", self.timeout)
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(self.timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)

    def handler(self, signum, frame):
        raise TimeoutException("Timeout ocurred")


class FTPClient:
    def __init__(
        self,
        ftp_user: str = FTP_USER,
        ftp_password: str = FTP_PASSWORD,
        ftp_host: str = FTP_HOST,
    ) -> None:
        for required, name in [
            (ftp_host, "FTP_HOST"),
            (ftp_user, "FTP_USER"),
            (ftp_password, "FTP_PASSWORD"),
        ]:
            if not required:
                raise ValueError(f"{name} not set")
        self.host = ftp_host
        self.username = ftp_user
        self.password = ftp_password
        self.connection = None

    def __enter__(self):
        with TimeoutContext(30):
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.quit()

    def connect(self) -> FTP:
        """
        Connect to the FTP server using provided credentials.
        Returns:
            FTP: An active FTP connection.
        """
        logger.info("Connecting to %s", self.host)
        if not self.connection:
            self.connection = FTP(self.host, encoding="latin-1")
        status = self.connection.login(self.username, self.password)
        logger.info("Status: %s", status)

    def level_up(self) -> None:
        """
        Move up one directory level on the FTP server.
        """
        self.connection.cwd("..")

    def get_dir_data(self, path: str) -> list[dict]:
        """
        Retrieve and parse directory listing from the FTP server.
        Args:
            path (str): The directory path to scan.
        Returns:
            list[dict]: A list of parsed file and directory information.
        """
        try:
            logger.info("Scanning %s", path)
            lines = []
            self.connection.dir(path, lines.append)
            parsed_files = []
            for line in lines:
                parsed = self.parse_line(path, line)
                if parsed:
                    parsed_files.append(parsed)
            return parsed_files
        except error_perm as e:
            logger.error("Error scanning %s: %s", path, e)
            with open("permission_errors.txt", "a", encoding="utf-8") as f:
                f.write(f"{path}\n")
            return []
        except OSError as e:
            logger.error("Error scanning %s: %s", path, e)
            return []
        except Exception as e:
            logger.error("Unexpected error scanning %s: %s", path, e)
            return []

    def parse_line(self, path: str, line: str) -> dict:
        """
        Parse a line from the FTP directory listing.
        Args:
            path (str): The directory path.
            line (str): A line from the directory listing.
        Returns:
            dict: Parsed file or directory information.
        """
        match = re.match(DIR_LIST_PATTERN, line.strip())
        if match:
            date_str, time_str, kind, filename = match.groups()
            date = datetime.strptime(date_str, DATE_FORMAT).date()
            time = datetime.strptime(time_str, TIME_FORMAT).time()
            created_at = datetime.combine(date, time).replace(tzinfo=UTC)
            return {
                "name": filename,
                "path": os.path.join(path, filename),
                "created_at": created_at,
                "is_dir": kind == "<DIR>",
            }
        else:
            logger.error("Line  %s does not match FTP pattern", line)
            return {}

    def get_files_at_depth(
        self, path: str, max_depth: int, current_depth: int = 0
    ) -> list[dict]:
        """
        Retrieve files at a specified depth from the given path.
        Depth 0 means the root path relative to BASE_FTP_PATH from env.
        Args:
            path (str): The starting directory path.
            max_depth (int): The maximum depth to scan.
            current_depth (int): The current depth in the recursion.
        Returns:
            list[dict]: A list of files found at the specified depth.
        """
        files = []
        while current_depth < max_depth:
            current_files = self.get_dir_data(path)
            current_depth += 1
            for file in current_files:
                if file["is_dir"]:
                    files.extend(
                        self.get_files_at_depth(
                            file["path"], max_depth, current_depth
                        )
                    )
                else:
                    files.append(file)
        return files

    def __str__(self) -> str:
        return f"FTP:{self.username}@{self.host}"


class SpectrumSaberClient:
    def __init__(self):
        self.__token__ = GRAPHQL_JWT_TOKEN
        self.__refresh_token__ = None
        self.user = None
        self.updated_token = False

    def __get_headers__(self) -> dict:
        """
        Construct headers for GraphQL requests, including auth token
        if available.
        Returns:
            dict: Headers for the request.
        """
        headers = {"Content-Type": "application/json"}
        if self.__token__:
            headers["Authorization"] = f"JWT {self.__token__}"
        return headers

    def __refresh_auth_token__(self) -> bool:
        """
        Refresh the authentication token using the refresh token.
        Returns:
            bool: True if the token was refreshed successfully,
            False otherwise.
        """
        if not self.__refresh_token__:
            logger.error(
                "No refresh token available to refresh authentication. "
                "Please register or login with your credentials."
            )
            return False
        query = """
        mutation RefreshToken ($refreshToken: String!, $revokeRefreshToken: Boolean!) {
            refreshToken (refreshToken: $refreshToken, revokeRefreshToken: $revokeRefreshToken) {
                success
                token {
                    token
                }
                errors
            }
        }
        """  # noqa: E501
        variables = {
            "refreshToken": self.__refresh_token__,
            "revokeRefreshToken": False,
        }
        result = self.query(query, variables)
        if result.get("data") and result["data"]["refreshToken"]["success"]:
            self.__token__ = result["data"]["refreshToken"]["token"]["token"]
            logger.info("Refreshed token successfully.")
            return True
        else:
            logger.error("Failed to refresh token: %s", result.get("errors"))
            return False

    def __verify_token__(self) -> bool:
        """
        Verify if the current token is valid by attempting a simple query.
        Returns:
            bool: True if token is valid, False otherwise.
        """
        query = """
        query {
            me {
                id
                username
            }
        }
        """
        payload = {"query": query}
        try:
            resp = requests.post(
                GRAPHQL_ENDPOINT,
                timeout=10,
                json=payload,
                headers=self.__get_headers__(),
            )
            data = resp.json()
            if data.get("errors"):
                return False
            if data.get("data") and data["data"].get("me"):
                self.user = data["data"]["me"]["username"]
                logger.info("Token verified for user: %s", self.user)
                return True
            return False
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error("Error verifying token: %s", e)
            return False

    def query(self, query: str, variables: dict | None = None) -> dict:
        """
        Execute a GraphQL query or mutation.
        Args:
            query (str): The GraphQL query or mutation string.
            variables (dict | None): Optional variables for the query.
        Returns:
            dict: The JSON response from the server.
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        resp = requests.post(
            GRAPHQL_ENDPOINT,
            timeout=10,
            json=payload,
            headers=self.__get_headers__(),
        )
        data = resp.json()
        if data.get("errors"):
            for error in data["errors"]:
                if "Unauthenticated" in error.get("message", ""):
                    logger.warning("Token expired, attempting to refresh.")
                    refreshed = self.__refresh_auth_token__()
                    if refreshed:
                        return self.query(query, variables)
        return data

    def login(self, username: str, password: str):
        """
        Authenticate the user with the given credentials.
        First attempts to use GRAPHQL_JWT_TOKEN from environment if available.
        If the env token is expired, proceeds with username/password auth.
        If successful, stores the auth and refresh tokens.
        Args:
            username (str): The username.
            password (str): The password.
        """
        # First, try to use token from environment variable
        if GRAPHQL_JWT_TOKEN:
            logger.info("Found GRAPHQL_JWT_TOKEN in environment, verifying...")
            if self.__verify_token__():
                logger.info(
                    "Using valid token from GRAPHQL_JWT_TOKEN "
                    "environment variable."
                )
                return
            else:
                logger.warning(
                    "Token from GRAPHQL_JWT_TOKEN is expired or invalid. "
                    "Proceeding with username/password authentication."
                )
                self.__token__ = None
                self.updated_token = True

        # Proceed with normal login
        query = """
        mutation TokenAuth($username: String!, $password: String!) {
            tokenAuth(username: $username, password: $password) {
                success
                token {
                    token
                }
                errors
                refreshToken {
                    token
                }
            }
        }
        """
        variables = {
            "username": username,
            "password": password,
        }
        result = self.query(query, variables)
        if result.get("data") and result["data"].get("tokenAuth", {}).get(
            "success"
        ):
            token_data = result["data"]["tokenAuth"].get("token")
            refresh_data = result["data"]["tokenAuth"].get("refreshToken")
            self.__token__ = (
                token_data["token"]
                if token_data and "token" in token_data
                else None
            )
            self.__refresh_token__ = (
                refresh_data["token"]
                if refresh_data and "token" in refresh_data
                else None
            )
            logger.info("Authenticated user %s.", username)

            # Notify user to update their environment variable
            if self.updated_token:
                print(
                    "\n" + "=" * 60 + "\n"
                    "Your GRAPHQL_JWT_TOKEN has been refreshed.\n"
                    "Please update your environment variable with "
                    "the new token:\n"
                    "export GRAPHQL_JWT_TOKEN='%s'\n" % self.__token__
                    + "=" * 60
                )
        else:
            logger.error(
                "Failed to authenticate user %s: %s",
                username,
                result.get("errors"),
            )

    def run_query(self, query: str, params: dict | None = None) -> dict | None:
        """
        Run a GraphQL query and return the data.
        Args:
            query (str): The GraphQL query string.
            params (dict | None): The parameters for the query (if any).
        Returns:
            dict: The JSON response from the server.
        """
        result = self.query(query, params)
        return result

    def logout(self):
        """
        Clear authentication tokens to log out the user.
        """
        self.__token__ = None
        self.__refresh_token__ = None
        self.user = None
        logger.info("User logged out successfully.")

    def is_authenticated(self) -> bool:
        """
        Check if the client is currently authenticated.
        Returns:
            bool: True if authenticated, False otherwise.
        """
        return self.__token__ is not None

    def get_token(self) -> str | None:
        """
        Get the current authentication token.
        Returns:
            str | None: The current token or None if not authenticated.
        """
        return self.__token__

    def text2gql(self, llm_provider, cache_schema: bool = True):
        """
        Create a Text2GQL instance bound to this client.

        Args:
            llm_provider: Any LLMProvider instance (use
                ``spectrumsaber.llm.create_provider`` to build one).
            cache_schema: Cache the introspected schema between calls
                          (default: True).

        Returns:
            A :class:`~spectrumsaber.text2gql.Text2GQL` instance ready
            to translate and execute natural-language queries.
        """
        from spectrumsaber.text2gql import Text2GQL

        return Text2GQL(self, llm_provider, cache_schema=cache_schema)


class InteractiveClient:  # pragma: no cover
    def __init__(self):
        self.ftp_client = FTPClient()
        self.saber_client = SpectrumSaberClient()

    def run(self):
        """
        Run the interactive client, allowing the user to login and
        interact with the FTP and GraphQL clients.
        """
        print("Welcome to the Spectrum Saber Interactive Client!")
        while True:
            print("\nPlease choose an option:")
            print("1. Login")
            print("2. Scan FTP Directory")
            print("3. Run GraphQL Query")
            print("4. Exit")
            choice = input("Enter your choice: ")
            if choice == "1":
                username = input("Username: ")
                password = input("Password: ")
                self.saber_client.login(username, password)
            elif choice == "2":
                path = input("Enter FTP directory path to scan: ")
                with self.ftp_client as ftp:
                    files = ftp.get_files_at_depth(path, max_depth=2)
                    for file in files:
                        print(file)
            elif choice == "3":
                query = input("Enter GraphQL query: ")
                result = self.saber_client.run_query(query)
                print(result)
            elif choice == "4":
                print("Goodbye!")
                break
            else:
                print("Invalid choice, please try again.")


class RichInteractiveClient:  # pragma: no cover
    """
    Enhanced interactive client using Rich console for better UX.
    """

    def __init__(self):
        self.console = Console()
        self.saber_client = SpectrumSaberClient()

    def display_banner(self):
        """
        Display a welcome banner.
        """
        banner = Panel.fit(
            "[bold cyan]Spectrum Saber GraphQL Client[/bold cyan]\n"
            "[dim]Interactive GraphQL Query Interface[/dim]",
            border_style="cyan",
        )
        self.console.print(banner)

    def display_menu(self):
        """
        Display the main menu.
        """
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan")
        table.add_column("Description")

        table.add_row("1", "Login")
        table.add_row("2", "Logout")
        table.add_row("3", "Show Token")
        table.add_row("4", "Run GraphQL Query")
        table.add_row("5", "Natural Language Query (Text-to-GraphQL)")
        table.add_row("6", "Exit")

        self.console.print("\n[bold]Menu:[/bold]")
        self.console.print(table)

    def handle_login(self):
        """
        Handle user login.
        """
        self.console.print("\n[bold yellow]Login[/bold yellow]")
        username = Prompt.ask("Username")
        password = Prompt.ask("Password", password=True)

        self.saber_client.login(username, password)

        if self.saber_client.is_authenticated():
            self.console.print("[bold green]✓[/bold green] Login successful!")
        else:
            self.console.print(
                "[bold red]✗[/bold red] Login failed. " "Check credentials."
            )

    def handle_logout(self):
        """
        Handle user logout.
        """
        if not self.saber_client.is_authenticated():
            self.console.print("[yellow]Not currently logged in.[/yellow]")
            return

        self.saber_client.logout()
        self.console.print(
            "[bold green]✓[/bold green] Logged out successfully."
        )

    def handle_show_token(self):
        """
        Display the current authentication token.
        """
        token = self.saber_client.get_token()
        if token:
            self.console.print("\n[bold]Current Token:[/bold]")
            self.console.print(Panel(token, border_style="green"))
        else:
            self.console.print(
                "[yellow]Not authenticated. Please login first.[/yellow]"
            )

    def handle_query(self):
        """
        Handle GraphQL query execution.
        """
        if not self.saber_client.is_authenticated():
            self.console.print(
                "[yellow]Not authenticated. Please login first.[/yellow]"
            )
            return

        self.console.print("\n[bold yellow]GraphQL Query[/bold yellow]")
        self.console.print(
            "[dim]Enter your query "
            "(press Ctrl+D or Ctrl+Z when done):[/dim]\n"
        )

        query_lines = []
        try:
            while True:
                line = input()
                query_lines.append(line)
        except EOFError:
            pass

        query = "\n".join(query_lines).strip()

        if not query:
            self.console.print("[red]Empty query. Aborting.[/red]")
            return

        # Ask for variables if needed
        has_variables = Confirm.ask("\nDoes this query need variables?")
        variables = None

        if has_variables:
            self.console.print("[dim]Enter variables as JSON:[/dim]")
            variables_str = Prompt.ask("Variables")
            try:
                variables = json.loads(variables_str)
            except json.JSONDecodeError:
                self.console.print(
                    "[red]Invalid JSON for variables."
                    " Proceeding without variables.[/red]"
                )
                variables = None

        # Execute query
        self.console.print("\n[dim]Executing query...[/dim]")
        result = self.saber_client.run_query(query, variables)

        # Display result
        self.display_result(result)

        # Ask to save
        if result and Confirm.ask("\nSave result to file?"):
            filename = Prompt.ask("Filename", default="query_result.json")
            self.save_result(result, filename)

    def display_result(self, result: dict):
        """
        Display query result with syntax highlighting.
        """
        self.console.print("\n[bold]Result:[/bold]")
        result_json = json.dumps(result, indent=2)
        syntax = Syntax(
            result_json, "json", theme="monokai", line_numbers=True
        )
        self.console.print(syntax)

    def save_result(self, result: dict, filename: str):
        """
        Save query result to a file.
        """
        try:
            filepath = Path(filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            self.console.print(
                f"[bold green]✓[/bold green] Saved to "
                f"{filepath.absolute()}"
            )
        except OSError as e:
            self.console.print(
                f"[bold red]✗[/bold red] Error saving file: {e}"
            )

    def handle_natural_query(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        """
        Start a natural-language → GraphQL REPL session.
        Prompts for LLM credentials if not supplied.
        """
        if not self.saber_client.is_authenticated():
            self.console.print(
                "[yellow]Not authenticated. Please login first.[/yellow]"
            )
            return

        from spectrumsaber.llm import create_provider

        if not provider:
            provider = Prompt.ask(
                "LLM provider", choices=["anthropic", "openai"]
            )
        if not api_key:
            api_key = Prompt.ask("API key", password=True)

        kwargs = {}
        if model:
            kwargs["model"] = model

        llm = create_provider(provider, api_key=api_key, **kwargs)
        t2gql = self.saber_client.text2gql(llm)

        self.console.print("[dim]Fetching schema…[/dim]", end=" ")
        try:
            schema = t2gql.fetch_schema()
            self.console.print(
                f"[green]✓[/green] [dim]{schema.count(chr(10))} lines[/dim]"
            )
        except RuntimeError as exc:
            self.console.print(
                f"[bold red]Failed to fetch schema:[/bold red] {exc}"
            )
            return

        self.console.print(
            Panel.fit(
                "[bold cyan]Natural Language Query[/bold cyan]\n"
                "[dim]Type your question in plain language. "
                "Enter [bold]exit[/bold] to go back.[/dim]",
                border_style="cyan",
            )
        )

        while True:
            try:
                text = Prompt.ask("\n[bold cyan]Query[/bold cyan]").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not text or text.lower() in ("exit", "quit", "q"):
                break
            try:
                gql = t2gql.translate(text)
                self.console.print(
                    "\n[bold cyan]Generated GraphQL:[/bold cyan]"
                )
                self.console.print(Syntax(gql, "graphql", theme="monokai"))
                result = t2gql.client.query(gql)
                self.display_result(result)
            except Exception as exc:  # noqa: BLE001
                self.console.print(f"[bold red]Error:[/bold red] {exc}")

    def run(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        """
        Run the interactive client loop.

        Args:
            provider: Pre-configured LLM provider name for text2gql.
            api_key:  Pre-configured LLM API key for text2gql.
            model:    Optional LLM model override for text2gql.
        """
        self.display_banner()

        while True:
            self.display_menu()

            choice = Prompt.ask(
                "\nChoose an option",
                choices=["1", "2", "3", "4", "5", "6"],
            )

            if choice == "1":
                self.handle_login()
            elif choice == "2":
                self.handle_logout()
            elif choice == "3":
                self.handle_show_token()
            elif choice == "4":
                self.handle_query()
            elif choice == "5":
                self.handle_natural_query(
                    provider=provider, api_key=api_key, model=model
                )
            elif choice == "6":
                self.console.print("\n[bold cyan]Goodbye![/bold cyan]")
                break


class CLIClient:
    """
    Non-interactive CLI client for scripting and automation.
    """

    def __init__(self):
        self.console = Console()
        self.saber_client = SpectrumSaberClient()

    def login(self, username: str, password: str) -> bool:
        """
        Login with credentials.
        """
        self.saber_client.login(username, password)
        return self.saber_client.is_authenticated()

    def get_token(self) -> str | None:
        """
        Get the authentication token.
        """
        return self.saber_client.get_token()

    def execute_query(self, query: str, variables: dict | None = None) -> dict:
        """
        Execute a GraphQL query.
        """
        return self.saber_client.run_query(query, variables)

    def save_to_file(self, data: dict, filepath: str):
        """
        Save data to a JSON file.
        """
        path = Path(filepath)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def main():
    """
    Main entry point for CLI usage.
    """
    parser = argparse.ArgumentParser(
        description="Spectrum Saber GraphQL Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--interactive", action="store_true", help="Run in interactive mode"
    )

    parser.add_argument(
        "--username", type=str, help="Username for authentication"
    )

    parser.add_argument(
        "--password", type=str, help="Password for authentication"
    )

    parser.add_argument("--query", type=str, help="GraphQL query to execute")

    parser.add_argument(
        "--query-file", type=str, help="Path to file containing GraphQL query"
    )

    parser.add_argument(
        "--variables", type=str, help="Query variables as JSON string"
    )

    parser.add_argument(
        "--variables-file",
        type=str,
        help="Path to file containing query variables (JSON)",
    )

    parser.add_argument(
        "--output", type=str, help="Output file path to save results"
    )

    parser.add_argument(
        "--show-token",
        action="store_true",
        help="Display the authentication token after login",
    )

    # Text-to-GraphQL options
    parser.add_argument(
        "--text2gql",
        action="store_true",
        help="Start an interactive natural-language → GraphQL REPL.",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default=os.getenv("LLM_PROVIDER"),
        help="LLM provider for --text2gql (or set LLM_PROVIDER env var).",
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        default=os.getenv("LLM_API_KEY"),
        help="LLM API key for --text2gql (or set LLM_API_KEY env var).",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        default=os.getenv("LLM_MODEL"),
        help="LLM model override for --text2gql (or set LLM_MODEL env var).",
    )

    args = parser.parse_args()

    # Text-to-GraphQL interactive REPL (standalone or as part of interactive)
    if args.text2gql:
        _run_text2gql_repl(args)
        return

    # Interactive mode
    if args.interactive:
        client = RichInteractiveClient()
        client.run(
            provider=args.provider,
            api_key=args.api_key,
            model=args.model,
        )
        return

    # CLI mode
    console = Console()
    cli_client = CLIClient()

    # Check if we need authentication
    if args.query or args.query_file or args.show_token:
        if cli_client.saber_client.is_authenticated():
            console.print(
                "[green]✓ Already authenticated using existing token.[/green]"
            )
        else:
            if not args.username or not args.password:
                console.print(
                    "[bold red]Error:[/bold red] Username and password "
                    "required for authentication."
                )
                sys.exit(1)

            console.print("[dim]Authenticating...[/dim]")
            success = cli_client.login(args.username, args.password)
            if not success:
                console.print(
                    "[bold red]Error:[/bold red] Authentication failed."
                )
                sys.exit(1)

            console.print("[green]✓ Authenticated[/green]")

        if args.show_token:
            token = cli_client.get_token()
            console.print(f"\nToken: {token}")

    # Execute query
    if args.query or args.query_file:
        # Get query
        if args.query_file:
            with open(args.query_file, "r", encoding="utf-8") as f:
                query = f.read()
        else:
            query = args.query

        # Get variables
        variables = None
        if args.variables:
            variables = json.loads(args.variables)
        elif args.variables_file:
            with open(args.variables_file, "r", encoding="utf-8") as f:
                variables = json.load(f)

        # Execute
        console.print("[dim]Executing query...[/dim]")
        result = cli_client.execute_query(query, variables)

        # Output
        if args.output:
            cli_client.save_to_file(result, args.output)
            console.print(f"[green]✓ Results saved to {args.output}[/green]")
        else:
            console.print("\n[bold]Result:[/bold]")
            console.print_json(data=result)

    # No action specified
    if (
        not args.interactive
        and not args.text2gql
        and not args.query
        and not args.query_file
        and not args.show_token
    ):
        parser.print_help()


def _run_text2gql_repl(args):  # pragma: no cover
    """
    Authenticate and start the Text-to-GraphQL interactive REPL.
    Called from both ``main()`` (via ``--text2gql``) and ``main_t2gql()``.
    """
    from spectrumsaber.llm import create_provider

    console = Console()

    # Resolve LLM credentials
    provider = args.provider
    api_key = getattr(args, "api_key", None) or os.getenv("LLM_API_KEY")
    model = getattr(args, "model", None)

    if not provider:
        console.print(
            "[bold red]Error:[/bold red] LLM provider required. "
            "Set LLM_PROVIDER env var or pass --provider anthropic|openai."
        )
        sys.exit(1)
    if not api_key:
        console.print(
            "[bold red]Error:[/bold red] LLM API key required. "
            "Set LLM_API_KEY env var or pass --api-key."
        )
        sys.exit(1)

    # Build and authenticate the saber client
    saber_client = SpectrumSaberClient()
    if not saber_client.is_authenticated():
        username = getattr(args, "username", None) or os.getenv(
            "GRAPHQL_USERNAME"
        )
        password = getattr(args, "password", None) or os.getenv(
            "GRAPHQL_PASSWORD"
        )
        if not username or not password:
            console.print(
                "[yellow]Warning:[/yellow] No JWT token found. "
                "Queries may fail. "
                "Set GRAPHQL_JWT_TOKEN or pass --username/--password."
            )
        else:
            console.print(f"[dim]Authenticating as {username}…[/dim]")
            saber_client.login(username, password)
            if not saber_client.is_authenticated():
                console.print("[bold red]Authentication failed.[/bold red]")
                sys.exit(1)
            console.print("[green]✓ Authenticated[/green]")

    # Build LLM provider
    kwargs = {}
    if model:
        kwargs["model"] = model
    llm = create_provider(provider, api_key=api_key, **kwargs)

    # Build Text2GQL
    cache = not getattr(args, "no_cache", False)
    t2gql = saber_client.text2gql(llm, cache_schema=cache)

    # Warm up schema
    console.print("[dim]Fetching schema…[/dim]", end=" ")
    try:
        schema = t2gql.fetch_schema()
        console.print(
            f"[green]✓[/green] [dim]{schema.count(chr(10))} lines[/dim]"
        )
    except RuntimeError as exc:
        console.print(f"\n[bold red]Failed to fetch schema:[/bold red] {exc}")
        sys.exit(1)

    console.print(
        Panel.fit(
            "[bold cyan]SpectrumSaber Text-to-GraphQL[/bold cyan]\n"
            "[dim]Type your query in plain language. "
            "Enter [bold]exit[/bold] or [bold]quit[/bold] to stop.[/dim]",
            border_style="cyan",
        )
    )

    while True:
        try:
            text = Prompt.ask("\n[bold cyan]Query[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold cyan]Bye![/bold cyan]")
            break
        if not text:
            continue
        if text.lower() in ("exit", "quit", "q"):
            console.print("[bold cyan]Bye![/bold cyan]")
            break
        try:
            gql = t2gql.translate(text)
            console.print("\n[bold cyan]Generated GraphQL:[/bold cyan]")
            console.print(Syntax(gql, "graphql", theme="monokai"))
            result = t2gql.client.query(gql)
            errors = result.get("errors")
            data = result.get("data")
            if errors:
                console.print("\n[bold red]GraphQL errors:[/bold red]")
                for err in errors:
                    console.print(f"  [red]• {err.get('message', err)}[/red]")
            if data is not None:
                console.print("\n[bold green]Result:[/bold green]")
                console.print_json(json.dumps(data))
        except Exception as exc:  # noqa: BLE001
            console.print(f"[bold red]Error:[/bold red] {exc}")


def main_t2gql():
    """
    Dedicated entry point for the ``spectrumsaber-t2gql`` command.

    Accepts the same --provider / --api-key / --model / --username /
    --password / --no-cache flags as ``spectrumsaber --text2gql``.
    """
    parser = argparse.ArgumentParser(
        description="SpectrumSaber Text-to-GraphQL interactive REPL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment variables:\n"
            "  GRAPHQL_JWT_TOKEN   JWT token (skip --username/--password)\n"
            "  LLM_PROVIDER        anthropic | openai\n"
            "  LLM_API_KEY         API key for the chosen LLM provider\n"
            "  LLM_MODEL           Optional model override\n"
            "  GRAPHQL_USERNAME    Used with --username if no JWT token\n"
            "  GRAPHQL_PASSWORD    Used with --password if no JWT token\n"
        ),
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default=os.getenv("LLM_PROVIDER"),
        help="LLM provider.",
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        default=os.getenv("LLM_API_KEY"),
        help="LLM API key.",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        default=os.getenv("LLM_MODEL"),
        help="LLM model override.",
    )
    parser.add_argument("--username", help="GraphQL username.")
    parser.add_argument("--password", help="GraphQL password.")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Re-fetch schema on every query.",
    )
    args = parser.parse_args()
    _run_text2gql_repl(args)


if __name__ == "__main__":
    main()
