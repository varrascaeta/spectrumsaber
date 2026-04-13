"""
Interactive client module for SpectrumSaber.

Contains: InteractiveClient, RichInteractiveClient — both pragma: no cover.
"""

# Standard imports
import json
import logging
from pathlib import Path

# Third-party imports
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

logger = logging.getLogger(__name__)


class InteractiveClient:  # pragma: no cover
    def __init__(self):
        import spectrumsaber.client as _client

        self.ftp_client = _client.FTPClient()
        self.saber_client = _client.SpectrumSaberClient()

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
        import spectrumsaber.client as _client

        self.console = Console()
        self.saber_client = _client.SpectrumSaberClient()

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

    def _natural_query_loop(self, t2gql) -> None:
        """Run the natural-language → GraphQL interactive loop."""
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

        self._natural_query_loop(t2gql)

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
