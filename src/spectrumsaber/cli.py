"""
CLI client module for SpectrumSaber.

Contains: CLIClient, _build_arg_parser, _cli_authenticate,
          _cli_execute_query, main, _validate_llm_args,
          _setup_saber_client_for_t2gql, _t2gql_repl_loop,
          _run_text2gql_repl, main_t2gql.
"""

# Standard imports
import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Third-party imports
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax

# Project imports
from spectrumsaber.interactive import RichInteractiveClient
from spectrumsaber.saber_client import SpectrumSaberClient

logger = logging.getLogger(__name__)


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


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="SpectrumSaber GraphQL Client",
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
        "--query-file",
        type=str,
        help="Path to file containing GraphQL query",
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
        help=(
            "LLM model override for --text2gql " "(or set LLM_MODEL env var)."
        ),
    )
    return parser


def _cli_authenticate(args, cli_client, console) -> None:
    """Authenticate cli_client when a query or --show-token is requested."""
    if not (args.query or args.query_file or args.show_token):
        return
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
            console.print("[bold red]Error:[/bold red] Authentication failed.")
            sys.exit(1)
        console.print("[green]✓ Authenticated[/green]")
    if args.show_token:
        token = cli_client.get_token()
        console.print(f"\nToken: {token}")


def _cli_execute_query(args, cli_client, console) -> None:
    """Execute a GraphQL query from CLI args and print or save the result."""
    if not (args.query or args.query_file):
        return
    if args.query_file:
        with open(args.query_file, "r", encoding="utf-8") as f:
            query = f.read()
    else:
        query = args.query
    variables = None
    if args.variables:
        variables = json.loads(args.variables)
    elif args.variables_file:
        with open(args.variables_file, "r", encoding="utf-8") as f:
            variables = json.load(f)
    console.print("[dim]Executing query...[/dim]")
    result = cli_client.execute_query(query, variables)
    if args.output:
        cli_client.save_to_file(result, args.output)
        console.print(f"[green]✓ Results saved to {args.output}[/green]")
    else:
        console.print("\n[bold]Result:[/bold]")
        console.print_json(data=result)


def main():
    """
    Main entry point for CLI usage.
    """
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.text2gql:
        _run_text2gql_repl(args)
        return

    if args.interactive:
        client = RichInteractiveClient()
        client.run(
            provider=args.provider,
            api_key=args.api_key,
            model=args.model,
        )
        return

    console = Console()
    cli_client = CLIClient()
    _cli_authenticate(args, cli_client, console)
    _cli_execute_query(args, cli_client, console)

    if not any([args.query, args.query_file, args.show_token]):
        parser.print_help()


def _validate_llm_args(args, console):  # pragma: no cover
    """Return (provider, api_key, model) or sys.exit if missing."""
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
    return provider, api_key, model


def _setup_saber_client_for_t2gql(args, console):  # pragma: no cover
    """Return an authenticated SpectrumSaberClient, or sys.exit on failure."""
    saber_client = SpectrumSaberClient()
    if saber_client.is_authenticated():
        return saber_client
    username = getattr(args, "username", None) or os.getenv("GRAPHQL_USERNAME")
    password = getattr(args, "password", None) or os.getenv("GRAPHQL_PASSWORD")
    if not username or not password:
        console.print(
            "[yellow]Warning:[/yellow] No JWT token found. "
            "Queries may fail. "
            "Set GRAPHQL_JWT_TOKEN or pass --username/--password."
        )
        return saber_client
    console.print(f"[dim]Authenticating as {username}…[/dim]")
    saber_client.login(username, password)
    if not saber_client.is_authenticated():
        console.print("[bold red]Authentication failed.[/bold red]")
        sys.exit(1)
    console.print("[green]✓ Authenticated[/green]")
    return saber_client


def _t2gql_repl_loop(t2gql, console) -> None:  # pragma: no cover
    """Run the text-to-GraphQL interactive REPL loop."""
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


def _run_text2gql_repl(args):  # pragma: no cover
    """
    Authenticate and start the Text-to-GraphQL interactive REPL.
    Called from both ``main()`` (via ``--text2gql``) and ``main_t2gql()``.
    """
    from spectrumsaber.llm import create_provider

    console = Console()
    provider, api_key, model = _validate_llm_args(args, console)
    saber_client = _setup_saber_client_for_t2gql(args, console)

    kwargs = {"model": model} if model else {}
    llm = create_provider(provider, api_key=api_key, **kwargs)

    cache = not getattr(args, "no_cache", False)
    t2gql = saber_client.text2gql(llm, cache_schema=cache)

    console.print("[dim]Fetching schema…[/dim]", end=" ")
    try:
        schema = t2gql.fetch_schema()
        console.print(
            f"[green]✓[/green] [dim]{schema.count(chr(10))} lines[/dim]"
        )
    except RuntimeError as exc:
        console.print(f"\n[bold red]Failed to fetch schema:[/bold red] {exc}")
        sys.exit(1)

    _t2gql_repl_loop(t2gql, console)


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
