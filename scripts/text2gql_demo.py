"""
text2gql_demo.py — interactive / one-shot text-to-GraphQL demo.

Required env vars:
  GRAPHQL_ENDPOINT      defaults to http://localhost:8000/graphql/
  GRAPHQL_JWT_TOKEN     JWT token (skip --username / --password if set)
  LLM_PROVIDER          "anthropic" or "openai"  (or pass --provider)
  LLM_API_KEY           API key for the chosen provider (or pass --api-key)

Optional env vars:
  LLM_MODEL             override model (e.g. "claude-haiku-4-5", "gpt-4o-mini")
  GRAPHQL_USERNAME      used with --login flag if no JWT token
  GRAPHQL_PASSWORD      used with --login flag if no JWT token

Usage examples:
  # One-shot query
  python scripts/text2gql_demo.py "Get all coverages"

  # Interactive REPL
  python scripts/text2gql_demo.py --interactive

  # Login with credentials instead of a JWT token
  python scripts/text2gql_demo.py --login --interactive

  # Choose provider / model on the fly
  python scripts/text2gql_demo.py --provider openai --api-key sk-... "List campaigns from CORDOBA"

  # Print only the generated GQL, do not execute
  python scripts/text2gql_demo.py --dry-run "Get all campaigns in 2023"
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax

load_dotenv()

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


def _build_client(args) -> "SpectrumSaberClient":  # noqa: F821
    from spectrumsaber.client import SpectrumSaberClient

    client = SpectrumSaberClient()

    if args.login:
        username = args.username or _env("GRAPHQL_USERNAME")
        password = args.password or _env("GRAPHQL_PASSWORD")
        if not username or not password:
            console.print(
                "[bold red]Error:[/bold red] --login requires "
                "GRAPHQL_USERNAME and GRAPHQL_PASSWORD (or --username/--password)."
            )
            sys.exit(1)
        console.print(f"[dim]Authenticating as {username}…[/dim]")
        client.login(username, password)
        if not client.is_authenticated():
            console.print("[bold red]Authentication failed.[/bold red]")
            sys.exit(1)
        console.print("[green]✓ Authenticated[/green]")
    elif not client.is_authenticated():
        console.print(
            "[yellow]Warning:[/yellow] No GRAPHQL_JWT_TOKEN found. "
            "Queries may fail. Use --login or set GRAPHQL_JWT_TOKEN."
        )

    return client


def _build_llm(args):
    from spectrumsaber.llm import create_provider

    provider = args.provider or _env("LLM_PROVIDER")
    api_key = args.api_key or _env("LLM_API_KEY")
    model = args.model or _env("LLM_MODEL")

    if not provider:
        console.print(
            "[bold red]Error:[/bold red] LLM provider required. "
            "Set LLM_PROVIDER env var or pass --provider anthropic|openai."
        )
        sys.exit(1)
    if not api_key:
        console.print(
            "[bold red]Error:[/bold red] API key required. "
            "Set LLM_API_KEY env var or pass --api-key."
        )
        sys.exit(1)

    kwargs = {}
    if model:
        kwargs["model"] = model

    return create_provider(provider, api_key=api_key, **kwargs)


def _print_query(gql: str) -> None:
    console.print("\n[bold cyan]Generated GraphQL query:[/bold cyan]")
    console.print(Syntax(gql, "graphql", theme="monokai"))


def _print_result(data: dict) -> None:
    errors = data.get("errors")
    result_data = data.get("data")

    if errors:
        console.print("\n[bold red]GraphQL errors:[/bold red]")
        for err in errors:
            console.print(f"  [red]• {err.get('message', err)}[/red]")

    if result_data is not None:
        console.print("\n[bold green]Result:[/bold green]")
        console.print_json(json.dumps(result_data))


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def run_once(t2gql, natural_text: str, dry_run: bool) -> None:
    console.print(
        Panel.fit(
            f"[bold]{natural_text}[/bold]",
            title="[dim]Natural language query[/dim]",
            border_style="dim",
        )
    )

    if dry_run:
        gql = t2gql.translate(natural_text)
        _print_query(gql)
    else:
        console.print("[dim]Translating and executing…[/dim]")
        gql = t2gql.translate(natural_text)
        _print_query(gql)
        result = t2gql.client.query(gql)
        _print_result(result)


def run_interactive(t2gql, dry_run: bool) -> None:
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
            natural_text = Prompt.ask("\n[bold cyan]Query[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold cyan]Bye![/bold cyan]")
            break

        if not natural_text:
            continue
        if natural_text.lower() in ("exit", "quit", "q"):
            console.print("[bold cyan]Bye![/bold cyan]")
            break

        try:
            run_once(t2gql, natural_text, dry_run)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[bold red]Error:[/bold red] {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Text-to-GraphQL demo for SpectrumSaber",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Natural language query to translate and execute.",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start an interactive REPL.",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Print the generated GQL but do not execute it.",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        help="LLM provider (overrides LLM_PROVIDER env var).",
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        help="LLM API key (overrides LLM_API_KEY env var).",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        help="LLM model name (overrides LLM_MODEL env var).",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Authenticate with username/password instead of JWT token.",
    )
    parser.add_argument("--username", help="GraphQL username (with --login).")
    parser.add_argument("--password", help="GraphQL password (with --login).")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable schema caching (re-fetch introspection every query).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.query and not args.interactive:
        # Default to interactive if nothing is specified
        args.interactive = True

    from spectrumsaber.text2gql import Text2GQL

    client = _build_client(args)
    llm = _build_llm(args)
    t2gql = Text2GQL(client, llm, cache_schema=not args.no_cache)

    # Warm up: fetch schema once so the first query feels snappy
    console.print("[dim]Fetching schema…[/dim]", end=" ")
    try:
        schema = t2gql.fetch_schema()
        line_count = schema.count("\n")
        console.print(f"[green]✓[/green] [dim]{line_count} lines[/dim]")
    except RuntimeError as exc:
        console.print(f"\n[bold red]Failed to fetch schema:[/bold red] {exc}")
        sys.exit(1)

    if args.interactive:
        run_interactive(t2gql, args.dry_run)
    else:
        run_once(t2gql, args.query, args.dry_run)


if __name__ == "__main__":
    main()
