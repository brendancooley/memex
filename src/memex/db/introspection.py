"""Schema introspection for memex database.

Provides structured representation of database schema for context injection
into LLM prompts.
"""

import sqlite3
from dataclasses import dataclass


@dataclass
class ColumnInfo:
    """Information about a database column."""

    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    default_value: str | None = None


@dataclass
class TableInfo:
    """Information about a database table."""

    name: str
    columns: list[ColumnInfo]

    def __repr__(self) -> str:
        """Return string representation with column count."""
        return f"TableInfo(name={self.name!r}, {len(self.columns)} columns)"

    def column_by_name(self, name: str) -> ColumnInfo | None:
        """Return column by name, or None if not found."""
        for col in self.columns:
            if col.name == name:
                return col
        return None


def get_schema(conn: sqlite3.Connection) -> dict[str, TableInfo]:
    """Read database schema and return structured representation.

    Queries sqlite_master for tables and PRAGMA table_info for columns.
    Excludes internal tables (sqlite_*, _schema_ops).

    Args:
        conn: Active database connection.

    Returns:
        Dictionary mapping table names to TableInfo objects.
    """
    schema: dict[str, TableInfo] = {}

    # Get all user tables (exclude sqlite_* and _schema_ops)
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        AND name != '_schema_ops'
        ORDER BY name
    """)

    for (table_name,) in cursor.fetchall():
        columns = _get_columns(conn, table_name)
        schema[table_name] = TableInfo(name=table_name, columns=columns)

    return schema


def _get_columns(conn: sqlite3.Connection, table_name: str) -> list[ColumnInfo]:
    """Get column info for a table using PRAGMA table_info.

    Args:
        conn: Active database connection.
        table_name: Name of table to introspect.

    Returns:
        List of ColumnInfo objects for each column.
    """
    # Quote table name for safety with special characters (spaces, quotes)
    # Double quotes inside name must be escaped by doubling them
    escaped_name = table_name.replace('"', '""')
    cursor = conn.execute(f'PRAGMA table_info("{escaped_name}")')
    columns: list[ColumnInfo] = []

    for row in cursor.fetchall():
        # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
        col = ColumnInfo(
            name=row[1],
            type=row[2],
            nullable=row[3] == 0,  # notnull=0 means nullable
            primary_key=row[5] == 1,
            default_value=row[4],
        )
        columns.append(col)

    return columns
