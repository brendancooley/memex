"""Tests for the memex CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from memex.cli import cli
from memex.db.connection import Database
from memex.ops.schema import ColumnDef, CreateTable
from memex.ops.schema import execute as schema_execute


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_memex_home(tmp_path: Path) -> Path:
    """Create a temporary MEMEX_HOME directory."""
    return tmp_path


class TestCLIHelp:
    """Test CLI help output."""

    def test_main_help(self, runner: CliRunner) -> None:
        """Main command shows help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Memex" in result.output
        assert "chat" in result.output
        assert "query" in result.output
        assert "status" in result.output

    def test_status_help(self, runner: CliRunner) -> None:
        """Status command has help."""
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0
        assert "schema" in result.output.lower()

    def test_query_help(self, runner: CliRunner) -> None:
        """Query command has help."""
        result = runner.invoke(cli, ["query", "--help"])
        assert result.exit_code == 0
        assert "SQL" in result.output


class TestStatusCommand:
    """Test mx status command."""

    def test_status_no_database(self, runner: CliRunner, temp_memex_home: Path) -> None:
        """Status with no database shows appropriate message."""
        result = runner.invoke(
            cli, ["status"], env={"MEMEX_HOME": str(temp_memex_home)}
        )
        assert result.exit_code == 0
        assert "not initialized" in result.output or "No" in result.output

    def test_status_empty_database(
        self, runner: CliRunner, temp_memex_home: Path
    ) -> None:
        """Status with empty database shows no tables."""
        # Create empty database
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)

        result = runner.invoke(
            cli, ["status"], env={"MEMEX_HOME": str(temp_memex_home)}
        )
        assert result.exit_code == 0
        assert "No user tables" in result.output

    def test_status_with_tables(self, runner: CliRunner, temp_memex_home: Path) -> None:
        """Status shows table information."""
        # Create database with a table
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            op = CreateTable(
                table="person",
                columns=[
                    ColumnDef(name="name", type="text", nullable=False),
                    ColumnDef(name="email", type="text", nullable=True),
                ],
            )
            schema_execute(db, conn, op)

        result = runner.invoke(
            cli, ["status"], env={"MEMEX_HOME": str(temp_memex_home)}
        )
        assert result.exit_code == 0
        assert "Tables:" in result.output
        assert "person" in result.output
        assert "name" in result.output


class TestQueryCommand:
    """Test mx query command."""

    def test_query_simple(self, runner: CliRunner, temp_memex_home: Path) -> None:
        """Query with simple SELECT works."""
        # Create database
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)

        result = runner.invoke(
            cli,
            ["query", "SELECT 1 as test"],
            env={"MEMEX_HOME": str(temp_memex_home)},
        )
        assert result.exit_code == 0
        assert "1" in result.output

    def test_query_table_data(self, runner: CliRunner, temp_memex_home: Path) -> None:
        """Query returns table data."""
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            op = CreateTable(
                table="person",
                columns=[ColumnDef(name="name", type="text", nullable=False)],
            )
            schema_execute(db, conn, op)
            conn.execute("INSERT INTO person (name) VALUES ('Alice')")

        result = runner.invoke(
            cli,
            ["query", "SELECT * FROM person"],
            env={"MEMEX_HOME": str(temp_memex_home)},
        )
        assert result.exit_code == 0
        assert "Alice" in result.output

    def test_query_no_results(self, runner: CliRunner, temp_memex_home: Path) -> None:
        """Query with no results shows message."""
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            op = CreateTable(
                table="person",
                columns=[ColumnDef(name="name", type="text", nullable=False)],
            )
            schema_execute(db, conn, op)

        result = runner.invoke(
            cli,
            ["query", "SELECT * FROM person WHERE 1=0"],
            env={"MEMEX_HOME": str(temp_memex_home)},
        )
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_query_invalid_sql(self, runner: CliRunner, temp_memex_home: Path) -> None:
        """Query with invalid SQL shows error."""
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)

        result = runner.invoke(
            cli,
            ["query", "SELEKT * FROM nowhere"],
            env={"MEMEX_HOME": str(temp_memex_home)},
        )
        assert result.exit_code == 1
        assert "Error" in result.output


class TestSandboxMode:
    """Test sandbox mode."""

    def test_sandbox_creates_temp_dir(self, runner: CliRunner) -> None:
        """Sandbox mode uses temp directory."""
        result = runner.invoke(cli, ["--sandbox", "status"])
        assert result.exit_code == 0
        assert "Sandbox mode:" in result.output
        assert "Sandbox cleaned up:" in result.output

    def test_sandbox_cleans_up(self, runner: CliRunner) -> None:
        """Sandbox directory is removed after exit."""
        result = runner.invoke(cli, ["--sandbox", "status"])
        # Extract the temp dir path from output
        for line in result.output.split("\n"):
            if "Sandbox mode:" in line:
                temp_dir = line.split("Sandbox mode:")[1].strip()
                assert not Path(temp_dir).exists()
                break


class TestChatCommand:
    """Test mx chat command."""

    def test_chat_requires_api_key(
        self, runner: CliRunner, temp_memex_home: Path
    ) -> None:
        """Chat command fails without API key."""
        result = runner.invoke(
            cli,
            ["chat"],
            env={"MEMEX_HOME": str(temp_memex_home), "ANTHROPIC_API_KEY": ""},
        )
        assert result.exit_code == 1
        assert "ANTHROPIC_API_KEY" in result.output


class TestResetCommand:
    """Test mx reset command."""

    def test_reset_no_database(self, runner: CliRunner, temp_memex_home: Path) -> None:
        """Reset with no database shows nothing to reset."""
        result = runner.invoke(
            cli,
            ["reset", "--confirm"],
            env={"MEMEX_HOME": str(temp_memex_home)},
        )
        assert result.exit_code == 0
        assert "Nothing to reset" in result.output

    def test_reset_requires_confirmation(
        self, runner: CliRunner, temp_memex_home: Path
    ) -> None:
        """Reset without --confirm prompts and can be aborted."""
        # Create database
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)

        # Simulate 'n' response to confirmation
        result = runner.invoke(
            cli,
            ["reset"],
            env={"MEMEX_HOME": str(temp_memex_home)},
            input="n\n",
        )
        assert result.exit_code == 0
        assert "Aborted" in result.output
        # Database should still exist
        assert (temp_memex_home / "memex.db").exists()

    def test_reset_with_confirm_deletes_database(
        self, runner: CliRunner, temp_memex_home: Path
    ) -> None:
        """Reset with --confirm deletes the database."""
        # Create database
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)

        assert (temp_memex_home / "memex.db").exists()

        result = runner.invoke(
            cli,
            ["reset", "--confirm"],
            env={"MEMEX_HOME": str(temp_memex_home)},
        )
        assert result.exit_code == 0
        assert "Database deleted" in result.output
        assert "Reset complete" in result.output
        assert not (temp_memex_home / "memex.db").exists()

    def test_reset_creates_archive(
        self, runner: CliRunner, temp_memex_home: Path
    ) -> None:
        """Reset creates an archive before deleting."""
        # Create database
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)

        result = runner.invoke(
            cli,
            ["reset", "--confirm"],
            env={"MEMEX_HOME": str(temp_memex_home)},
        )
        assert result.exit_code == 0
        assert "Archived to:" in result.output

        # Archive directory should exist with a file
        archive_dir = temp_memex_home / "archive"
        assert archive_dir.exists()
        archives = list(archive_dir.glob("memex_*.db"))
        assert len(archives) == 1

    def test_reset_no_archive_skips_archiving(
        self, runner: CliRunner, temp_memex_home: Path
    ) -> None:
        """Reset with --no-archive skips archiving."""
        # Create database
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)

        result = runner.invoke(
            cli,
            ["reset", "--confirm", "--no-archive"],
            env={"MEMEX_HOME": str(temp_memex_home)},
        )
        assert result.exit_code == 0
        assert "Archived to:" not in result.output
        assert "Database deleted" in result.output

        # Archive directory should not exist
        archive_dir = temp_memex_home / "archive"
        assert not archive_dir.exists()

    def test_reset_interactive_confirmation(
        self, runner: CliRunner, temp_memex_home: Path
    ) -> None:
        """Reset with 'y' response proceeds."""
        # Create database
        db = Database(temp_memex_home / "memex.db")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)

        result = runner.invoke(
            cli,
            ["reset"],
            env={"MEMEX_HOME": str(temp_memex_home)},
            input="y\n",
        )
        assert result.exit_code == 0
        assert "Database deleted" in result.output
        assert not (temp_memex_home / "memex.db").exists()
