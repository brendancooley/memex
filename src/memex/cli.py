"""Memex CLI - Terminal interface for the personal knowledge system.

Provides the `mx` command for interacting with memex:
    mx          Interactive chat mode (default)
    mx chat     Explicit chat mode
    mx query    Direct SQL query
    mx status   Show schema summary
    mx reset    Destroy all data (with safeguards)
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown

from memex.agent import DEFAULT_MODEL, AgentDeps, create_agent
from memex.db.connection import Database, get_db_path
from memex.db.introspection import get_schema
from memex.ops.query import Query
from memex.ops.query import execute as query_execute

if TYPE_CHECKING:
    from pydantic_ai import Agent

console = Console()


def _get_history_path() -> Path:
    """Return path to the CLI history file."""
    memex_home = os.environ.get("MEMEX_HOME")
    if memex_home:
        return Path(memex_home) / ".mx_history"
    return Path.home() / ".memex" / ".mx_history"


def _check_api_key() -> bool:
    """Check if Anthropic API key is configured."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _run_chat_loop(agent: Agent[AgentDeps, str], db: Database) -> None:
    """Run the interactive chat loop.

    Args:
        agent: Configured memex agent.
        db: Database instance.
    """
    history_path = _get_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)

    session: PromptSession[str] = PromptSession(history=FileHistory(str(history_path)))

    console.print("[dim]Memex ready. Type 'exit' or Ctrl+D to quit.[/dim]\n")

    deps = AgentDeps(db=db)

    while True:
        try:
            user_input = session.prompt("mx> ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        try:
            result = agent.run_sync(user_input, deps=deps)
            console.print()
            console.print(Markdown(result.output))
            console.print()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]", highlight=False)


@click.group(invoke_without_command=True)
@click.option(
    "--sandbox",
    is_flag=True,
    help="Use ephemeral database (temp directory, deleted on exit)",
)
@click.pass_context
def cli(ctx: click.Context, sandbox: bool) -> None:
    """Memex - A personal knowledge system you talk to like a friend.

    Run without arguments to start interactive chat.
    """
    ctx.ensure_object(dict)

    if sandbox:
        # Create temp directory for sandbox mode
        temp_dir = tempfile.mkdtemp(prefix="memex_sandbox_")
        os.environ["MEMEX_HOME"] = temp_dir
        ctx.obj["sandbox_dir"] = temp_dir
        click.echo(f"Sandbox mode: {temp_dir}", err=True)

    ctx.obj["db_path"] = get_db_path()

    # If no subcommand, run chat
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


@cli.result_callback()
@click.pass_context
def cleanup(ctx: click.Context, _result: object, **_kwargs) -> None:
    """Clean up sandbox directory if used."""
    sandbox_dir = ctx.obj.get("sandbox_dir")
    if sandbox_dir and Path(sandbox_dir).exists():
        shutil.rmtree(sandbox_dir)
        click.echo(f"Sandbox cleaned up: {sandbox_dir}", err=True)


@cli.command()
@click.pass_context
def chat(ctx: click.Context) -> None:
    """Start interactive chat with memex."""
    if not _check_api_key():
        click.echo(
            "Error: ANTHROPIC_API_KEY not set. "
            "Get your key at https://console.anthropic.com/",
            err=True,
        )
        raise SystemExit(1)

    db_path: Path = ctx.obj["db_path"]
    db = Database(db_path)
    agent = create_agent(DEFAULT_MODEL)

    _run_chat_loop(agent, db)


@cli.command()
@click.argument("sql")
@click.pass_context
def query(ctx: click.Context, sql: str) -> None:
    """Execute a SQL query directly.

    Example: mx query "SELECT * FROM person"
    """
    db_path: Path = ctx.obj["db_path"]
    db = Database(db_path)

    try:
        op = Query(sql=sql, params={})
        with db.connect() as conn:
            rows = query_execute(conn, op)

        if not rows:
            click.echo("No results")
            return

        # Print results as a table
        for row in rows:
            click.echo(row)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show database schema summary."""
    db_path: Path = ctx.obj["db_path"]
    db = Database(db_path)

    if not db_path.exists():
        click.echo("Database not initialized (no tables yet)")
        return

    try:
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            schema = get_schema(conn)

        if not schema:
            click.echo("No user tables found")
            return

        click.echo("Tables:")
        for table_name in sorted(schema.keys()):
            table = schema[table_name]
            col_info = []
            for col in table.columns:
                col_str = col.name
                if not col.nullable:
                    col_str += "*"
                col_info.append(col_str)
            click.echo(f"  {table_name}: {', '.join(col_info)}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None


def _get_memex_home() -> Path:
    """Return the memex home directory."""
    memex_home = os.environ.get("MEMEX_HOME")
    if memex_home:
        return Path(memex_home)
    return Path.home() / ".memex"


def _archive_memex_data(memex_home: Path) -> Path | None:
    """Archive memex data to the archive directory.

    Creates a timestamped copy of the memex.db file in ~/.memex/archive/.

    Args:
        memex_home: Path to the memex home directory.

    Returns:
        Path to the archive file, or None if there was nothing to archive.
    """
    db_path = memex_home / "memex.db"
    if not db_path.exists():
        return None

    archive_dir = memex_home / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = archive_dir / f"memex_{timestamp}.db"
    shutil.copy2(db_path, archive_path)

    return archive_path


@cli.command()
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--no-archive",
    is_flag=True,
    help="Skip archiving before reset (destructive)",
)
@click.pass_context
def reset(ctx: click.Context, confirm: bool, no_archive: bool) -> None:
    """Destroy all memex data.

    By default, archives the database before deletion. Use --no-archive
    to skip archiving (not recommended).

    Requires --confirm flag or interactive confirmation.
    """
    memex_home = _get_memex_home()
    db_path: Path = ctx.obj["db_path"]

    # Check if there's anything to reset
    if not db_path.exists():
        click.echo("Nothing to reset (database does not exist)")
        return

    # Show what will be deleted
    click.echo("This will DELETE all memex data:")
    click.echo(f"  Database: {db_path}")

    if not no_archive:
        click.echo(f"  (Will archive to: {memex_home / 'archive'})")
    else:
        click.echo("  WARNING: --no-archive specified, data will be permanently lost!")

    # Require confirmation
    if not confirm and not click.confirm("\nAre you sure you want to proceed?"):
        click.echo("Aborted")
        return

    # Archive first (unless --no-archive)
    if not no_archive:
        archive_path = _archive_memex_data(memex_home)
        if archive_path:
            click.echo(f"Archived to: {archive_path}")

    # Delete the database
    db_path.unlink()
    click.echo("Database deleted")

    # Also clean up history file
    history_path = _get_history_path()
    if history_path.exists():
        history_path.unlink()
        click.echo("History cleared")

    click.echo("Reset complete")


def main() -> None:
    """Entry point for the mx CLI."""
    cli()


if __name__ == "__main__":
    main()
