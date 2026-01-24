"""Query operations with Pydantic models and executor.

Provides typed models for CRUD operations and an executor function
that generates and runs parameterized SQL against SQLite connections.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, overload

if TYPE_CHECKING:
    import sqlite3

from pydantic import BaseModel, field_validator, model_validator

# Valid names: alphanumeric + underscore, cannot start with digit
_VALID_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_name(name: str) -> str:
    """Validate that a name is valid for a table or column.

    Args:
        name: The name to validate.

    Returns:
        The validated name.

    Raises:
        ValueError: If the name is invalid.
    """
    if not name or not _VALID_NAME_PATTERN.match(name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return name


class Query(BaseModel):
    """A SELECT query with optional parameters.

    Attributes:
        sql: The SQL query string (must start with SELECT).
        params: Named parameters for the query (default empty dict).
    """

    sql: str
    params: dict[str, Any] = {}

    @field_validator("sql")
    @classmethod
    def validate_is_select(cls, v: str) -> str:
        """Validate that SQL starts with SELECT."""
        stripped = v.strip()
        if not stripped.upper().startswith("SELECT"):
            msg = "Query SQL must start with SELECT"
            raise ValueError(msg)
        return v


class Insert(BaseModel):
    """An INSERT operation for a single row.

    Attributes:
        table: Target table name.
        data: Column-value pairs to insert.
    """

    table: str
    data: dict[str, Any]

    @field_validator("table")
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name is alphanumeric + underscore."""
        return _validate_name(v)

    @model_validator(mode="after")
    def validate_data(self) -> Insert:
        """Validate that data is non-empty and column names are valid."""
        if not self.data:
            raise ValueError("data cannot be empty")
        for col in self.data:
            _validate_name(col)
        return self


class Update(BaseModel):
    """An UPDATE operation for a single row by id.

    Attributes:
        table: Target table name.
        id: Row id to update.
        data: Column-value pairs to update.
    """

    table: str
    id: int
    data: dict[str, Any]

    @field_validator("table")
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name is alphanumeric + underscore."""
        return _validate_name(v)

    @model_validator(mode="after")
    def validate_data(self) -> Update:
        """Validate that data is non-empty and column names are valid."""
        if not self.data:
            raise ValueError("data cannot be empty")
        for col in self.data:
            _validate_name(col)
        return self


class Delete(BaseModel):
    """A DELETE operation for a single row by id.

    Attributes:
        table: Target table name.
        id: Row id to delete.
    """

    table: str
    id: int

    @field_validator("table")
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name is alphanumeric + underscore."""
        return _validate_name(v)


@overload
def execute(conn: sqlite3.Connection, op: Query) -> list[tuple[Any, ...]]: ...


@overload
def execute(conn: sqlite3.Connection, op: Insert) -> int: ...


@overload
def execute(conn: sqlite3.Connection, op: Update) -> None: ...


@overload
def execute(conn: sqlite3.Connection, op: Delete) -> None: ...


def execute(
    conn: sqlite3.Connection, op: Query | Insert | Update | Delete
) -> list[tuple[Any, ...]] | int | None:
    """Execute a database operation and return appropriate result.

    Args:
        conn: Active SQLite connection.
        op: The operation to execute (Query, Insert, Update, or Delete).

    Returns:
        For Query: List of tuples (rows).
        For Insert: The new row id (int).
        For Update/Delete: None.

    Raises:
        ValueError: If Update/Delete targets a non-existent row.
    """
    if isinstance(op, Query):
        return _execute_query(conn, op)
    if isinstance(op, Insert):
        return _execute_insert(conn, op)
    if isinstance(op, Update):
        return _execute_update(conn, op)
    if isinstance(op, Delete):
        return _execute_delete(conn, op)
    msg = f"Unknown operation type: {type(op)}"
    raise TypeError(msg)


def _execute_query(conn: sqlite3.Connection, op: Query) -> list[tuple[Any, ...]]:
    """Execute a SELECT query and return rows."""
    cursor = conn.execute(op.sql, op.params)
    return cursor.fetchall()


def _execute_insert(conn: sqlite3.Connection, op: Insert) -> int:
    """Execute an INSERT and return the new row id."""
    columns = list(op.data.keys())
    placeholders = ", ".join(f":{col}" for col in columns)
    column_list = ", ".join(columns)

    sql = f"INSERT INTO {op.table} ({column_list}) VALUES ({placeholders})"
    cursor = conn.execute(sql, op.data)

    return cursor.lastrowid  # type: ignore[return-value]


def _execute_update(conn: sqlite3.Connection, op: Update) -> None:
    """Execute an UPDATE for a row by id."""
    # LBYL: Check if row exists before updating
    cursor = conn.execute(f"SELECT 1 FROM {op.table} WHERE id = :id", {"id": op.id})
    if cursor.fetchone() is None:
        msg = f"Row with id {op.id} not found in table {op.table}"
        raise ValueError(msg)

    set_clause = ", ".join(f"{col} = :{col}" for col in op.data)
    params = {**op.data, "id": op.id}

    sql = f"UPDATE {op.table} SET {set_clause} WHERE id = :id"
    conn.execute(sql, params)


def _execute_delete(conn: sqlite3.Connection, op: Delete) -> None:
    """Execute a DELETE for a row by id."""
    # LBYL: Check if row exists before deleting
    cursor = conn.execute(f"SELECT 1 FROM {op.table} WHERE id = :id", {"id": op.id})
    if cursor.fetchone() is None:
        msg = f"Row with id {op.id} not found in table {op.table}"
        raise ValueError(msg)

    sql = f"DELETE FROM {op.table} WHERE id = :id"
    conn.execute(sql, {"id": op.id})
