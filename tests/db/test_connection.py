"""Tests for database connection manager."""

import tempfile
from pathlib import Path

import pytest

from memex.db.connection import (
    Database,
    get_db_path,
)


class TestGetDbPath:
    """Tests for get_db_path function."""

    def test_returns_memex_home_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns path from MEMEX_HOME env var when set."""
        monkeypatch.setenv("MEMEX_HOME", "/custom/path")
        result = get_db_path()
        assert result == Path("/custom/path/memex.db")

    def test_returns_default_when_memex_home_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns ~/.memex/memex.db when MEMEX_HOME not set."""
        monkeypatch.delenv("MEMEX_HOME", raising=False)
        result = get_db_path()
        assert result == Path.home() / ".memex" / "memex.db"


class TestDatabase:
    """Tests for Database connection manager."""

    def test_creates_parent_directory_if_not_exists(self) -> None:
        """Database creates parent directory when connecting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "subdir" / "test.db"
            db = Database(db_path)
            with db.connect():
                pass
            assert db_path.parent.exists()

    def test_connect_returns_connection(self) -> None:
        """connect() returns a working SQLite connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            with db.connect() as conn:
                cursor = conn.execute("SELECT 1")
                assert cursor.fetchone() == (1,)

    def test_connect_auto_commits_on_success(self) -> None:
        """connect() commits transaction on successful context exit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            with db.connect() as conn:
                conn.execute("CREATE TABLE test (id INTEGER)")
                conn.execute("INSERT INTO test VALUES (42)")

            # Verify data persisted
            with db.connect() as conn:
                cursor = conn.execute("SELECT id FROM test")
                assert cursor.fetchone() == (42,)

    def test_connect_rolls_back_on_exception(self) -> None:
        """connect() rolls back transaction when exception raised."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)

            # Create table first
            with db.connect() as conn:
                conn.execute("CREATE TABLE test (id INTEGER)")

            # Attempt insert that raises
            with pytest.raises(ValueError), db.connect() as conn:
                conn.execute("INSERT INTO test VALUES (42)")
                raise ValueError("test error")

            # Verify rollback happened
            with db.connect() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM test")
                assert cursor.fetchone() == (0,)

    def test_in_memory_database(self) -> None:
        """Database works with in-memory SQLite."""
        db = Database(":memory:")
        with db.connect() as conn:
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.execute("INSERT INTO test VALUES (1)")
            cursor = conn.execute("SELECT id FROM test")
            assert cursor.fetchone() == (1,)

    def test_path_property(self) -> None:
        """Database exposes path property."""
        db = Database(Path("/some/path.db"))
        assert db.path == Path("/some/path.db")

    def test_path_property_with_string(self) -> None:
        """Database accepts string path and converts to Path."""
        db = Database("/some/path.db")
        assert db.path == Path("/some/path.db")

    def test_path_property_memory(self) -> None:
        """Database path is ':memory:' for in-memory db."""
        db = Database(":memory:")
        assert db.path == Path(":memory:")


class TestSchemaOpsTable:
    """Tests for _schema_ops migration tracking table."""

    def test_ensure_schema_ops_creates_table(self) -> None:
        """ensure_schema_ops() creates _schema_ops table if not exists."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='_schema_ops'"
            )
            assert cursor.fetchone() is not None

    def test_schema_ops_table_structure(self) -> None:
        """_schema_ops table has correct columns."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            cursor = conn.execute("PRAGMA table_info(_schema_ops)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            assert "id" in columns
            assert "op_type" in columns
            assert "op_json" in columns
            assert "applied_at" in columns

    def test_schema_ops_idempotent(self) -> None:
        """ensure_schema_ops() is idempotent."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            db.ensure_schema_ops(conn)  # Should not raise
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name='_schema_ops'"
            )
            assert cursor.fetchone() == (1,)

    def test_record_schema_op(self) -> None:
        """record_schema_op() inserts operation record."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            db.record_schema_op(
                conn,
                op_type="create_table",
                op_json='{"table": "users", "columns": ["id", "name"]}',
            )

            cursor = conn.execute("SELECT op_type, op_json FROM _schema_ops")
            row = cursor.fetchone()
            assert row[0] == "create_table"
            assert row[1] == '{"table": "users", "columns": ["id", "name"]}'

    def test_record_schema_op_auto_timestamp(self) -> None:
        """record_schema_op() auto-sets applied_at timestamp."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            db.record_schema_op(conn, op_type="test", op_json="{}")

            cursor = conn.execute("SELECT applied_at FROM _schema_ops")
            row = cursor.fetchone()
            assert row[0] is not None  # Timestamp was set
