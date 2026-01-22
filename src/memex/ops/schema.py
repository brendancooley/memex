"""Schema operations: Pydantic models, DDL transpiler, and executor.

Provides structured schema modification operations that can be:
1. Validated by Pydantic
2. Transpiled to DDL SQL
3. Executed against the database with audit logging
"""

import re
import sqlite3
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from memex.db.connection import Database

# Valid column types for SQLite
ColumnType = Literal["text", "integer", "real", "date", "datetime", "boolean"]

# Valid names: alphanumeric + underscore, cannot start with digit
_VALID_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class InvalidNameError(ValueError):
    """Raised when a table or column name is invalid."""


def _validate_name(name: str, entity: str) -> str:
    """Validate that a name is valid for a table or column.

    Args:
        name: The name to validate.
        entity: Description of what's being validated (for error message).

    Returns:
        The validated name.

    Raises:
        InvalidNameError: If the name is invalid.
    """
    if not name:
        raise InvalidNameError(f"{entity} name cannot be empty")
    if not _VALID_NAME_PATTERN.match(name):
        raise InvalidNameError(
            f"Invalid {entity} name '{name}': must be alphanumeric with underscores, "
            "cannot start with a digit"
        )
    return name


class ColumnDef(BaseModel):
    """Definition of a database column."""

    name: str
    type: ColumnType
    nullable: bool = True

    @field_validator("name")
    @classmethod
    def validate_column_name(cls, v: str) -> str:
        """Validate column name is alphanumeric + underscore."""
        return _validate_name(v, "column")


class CreateTable(BaseModel):
    """Operation to create a new table."""

    table: str
    columns: list[ColumnDef]

    @field_validator("table")
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name is alphanumeric + underscore."""
        return _validate_name(v, "table")

    @model_validator(mode="after")
    def validate_columns(self) -> "CreateTable":
        """Validate columns: at least one required, 'id' forbidden (auto-managed)."""
        if not self.columns:
            raise ValueError("Table must have at least one column")
        for col in self.columns:
            if col.name.lower() == "id":
                raise ValueError(
                    "Column 'id' is auto-managed and cannot be specified; "
                    "it is added automatically as PRIMARY KEY"
                )
        return self


class AddColumn(BaseModel):
    """Operation to add a column to an existing table."""

    table: str
    column: str
    type: ColumnType
    nullable: bool = True

    @field_validator("table")
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name is alphanumeric + underscore."""
        return _validate_name(v, "table")

    @field_validator("column")
    @classmethod
    def validate_column_name(cls, v: str) -> str:
        """Validate column name is alphanumeric + underscore."""
        return _validate_name(v, "column")


class DropColumn(BaseModel):
    """Operation to drop a column from a table."""

    table: str
    column: str

    @field_validator("table")
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name is alphanumeric + underscore."""
        return _validate_name(v, "table")

    @field_validator("column")
    @classmethod
    def validate_column_name(cls, v: str) -> str:
        """Validate column name is alphanumeric + underscore."""
        return _validate_name(v, "column")


# Union type for all schema operations
SchemaOp = CreateTable | AddColumn | DropColumn

# Map column type names to SQLite type names
_TYPE_MAP: dict[ColumnType, str] = {
    "text": "TEXT",
    "integer": "INTEGER",
    "real": "REAL",
    "date": "DATE",
    "datetime": "DATETIME",
    "boolean": "BOOLEAN",
}


def _column_def(col: ColumnDef) -> str:
    """Convert a ColumnDef to SQL column definition string.

    Args:
        col: The column definition.

    Returns:
        SQL column definition (e.g., "name TEXT NOT NULL").
    """
    sql_type = _TYPE_MAP[col.type]
    nullable_clause = "" if col.nullable else " NOT NULL"
    return f"{col.name} {sql_type}{nullable_clause}"


def _transpile_create_table(op: CreateTable) -> str:
    """Transpile CreateTable operation to SQL.

    Always prepends an auto-increment id column for CRUD compatibility.
    Insert uses cursor.lastrowid (works without explicit id), but
    Update/Delete hardcode WHERE id = :id, requiring the id column.

    Args:
        op: The CreateTable operation.

    Returns:
        CREATE TABLE SQL statement.
    """
    # Always add id column first for CRUD compatibility
    col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    col_defs.extend(_column_def(col) for col in op.columns)
    columns_sql = ", ".join(col_defs)
    return f"CREATE TABLE {op.table} ({columns_sql})"


def _transpile_add_column(op: AddColumn) -> str:
    """Transpile AddColumn operation to SQL.

    Args:
        op: The AddColumn operation.

    Returns:
        ALTER TABLE ADD COLUMN SQL statement.
    """
    sql_type = _TYPE_MAP[op.type]
    nullable_clause = "" if op.nullable else " NOT NULL"
    return f"ALTER TABLE {op.table} ADD COLUMN {op.column} {sql_type}{nullable_clause}"


def _transpile_drop_column(op: DropColumn) -> str:
    """Transpile DropColumn operation to SQL.

    Args:
        op: The DropColumn operation.

    Returns:
        ALTER TABLE DROP COLUMN SQL statement.
    """
    return f"ALTER TABLE {op.table} DROP COLUMN {op.column}"


def transpile(op: SchemaOp) -> str:
    """Transpile a schema operation to SQL DDL.

    Args:
        op: The schema operation to transpile.

    Returns:
        SQL DDL statement.
    """
    if isinstance(op, CreateTable):
        return _transpile_create_table(op)
    if isinstance(op, AddColumn):
        return _transpile_add_column(op)
    if isinstance(op, DropColumn):
        return _transpile_drop_column(op)
    # This should never happen due to type system, but satisfies exhaustiveness
    raise TypeError(f"Unknown operation type: {type(op)}")


def _get_op_type(op: SchemaOp) -> str:
    """Get the operation type string for recording.

    Args:
        op: The schema operation.

    Returns:
        Operation type string (e.g., 'create_table').
    """
    if isinstance(op, CreateTable):
        return "create_table"
    if isinstance(op, AddColumn):
        return "add_column"
    if isinstance(op, DropColumn):
        return "drop_column"
    raise TypeError(f"Unknown operation type: {type(op)}")


def execute(db: Database, conn: sqlite3.Connection, op: SchemaOp) -> None:
    """Execute a schema operation against the database.

    Executes the DDL and records the operation in _schema_ops.

    Args:
        db: Database instance (for recording schema op).
        conn: Active database connection.
        op: The schema operation to execute.
    """
    sql = transpile(op)
    conn.execute(sql)

    op_type = _get_op_type(op)
    op_json = op.model_dump_json()
    db.record_schema_op(conn, op_type, op_json)
