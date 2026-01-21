"""Database connection manager for memex.

Provides SQLite connection management with transaction support and
migration tracking via the _schema_ops table.
"""

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


def get_db_path() -> Path:
    """Return the path to the memex database.

    Uses MEMEX_HOME environment variable if set, otherwise defaults
    to ~/.memex/memex.db.
    """
    memex_home = os.environ.get("MEMEX_HOME")
    if memex_home:
        return Path(memex_home) / "memex.db"
    return Path.home() / ".memex" / "memex.db"


class Database:
    """SQLite connection manager with transaction support.

    Handles database file creation, connection pooling, and provides
    a context manager for automatic transaction handling.
    """

    def __init__(self, path: Path | str) -> None:
        """Initialize database with path.

        Args:
            path: Path to SQLite database file, or ':memory:' for in-memory db.
        """
        self._path = Path(path) if not isinstance(path, Path) else path

    @property
    def path(self) -> Path:
        """Return the database file path."""
        return self._path

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection]:
        """Context manager for database connections with transaction support.

        Creates parent directory if needed. Commits on successful exit,
        rolls back on exception.

        Yields:
            SQLite connection object.
        """
        # Create parent directory for file-based databases
        if self._path != Path(":memory:") and self._path.parent.name:
            self._path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self._path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_schema_ops(self, conn: sqlite3.Connection) -> None:
        """Ensure _schema_ops table exists for migration tracking.

        Creates the table if it doesn't exist. Idempotent.

        Args:
            conn: Active database connection.
        """
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _schema_ops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                op_type TEXT NOT NULL,
                op_json TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

    def record_schema_op(
        self, conn: sqlite3.Connection, op_type: str, op_json: str
    ) -> None:
        """Record a schema operation for auditability.

        Args:
            conn: Active database connection.
            op_type: Type of operation (e.g., 'create_table', 'add_column').
            op_json: JSON string describing the operation details.
        """
        conn.execute(
            "INSERT INTO _schema_ops (op_type, op_json) VALUES (?, ?)",
            (op_type, op_json),
        )
