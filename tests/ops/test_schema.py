"""Tests for schema operations: Pydantic models, DDL transpiler, and executor."""

import pytest
from pydantic import ValidationError

from memex.db.connection import Database
from memex.db.introspection import get_schema
from memex.ops.schema import (
    AddColumn,
    ColumnDef,
    CreateTable,
    DropColumn,
    SchemaOp,
    execute,
    transpile,
)


class TestColumnDef:
    """Tests for ColumnDef model."""

    def test_creates_text_column(self) -> None:
        """Creates a text column with defaults."""
        col = ColumnDef(name="title", type="text")
        assert col.name == "title"
        assert col.type == "text"
        assert col.nullable is True

    def test_creates_non_nullable_column(self) -> None:
        """Creates a non-nullable column."""
        col = ColumnDef(name="id", type="integer", nullable=False)
        assert col.nullable is False

    def test_validates_column_type(self) -> None:
        """Rejects invalid column types."""
        with pytest.raises(ValueError):
            ColumnDef(name="field", type="invalid")  # type: ignore[arg-type]

    def test_all_valid_types(self) -> None:
        """Accepts all valid column types."""
        valid_types = ["text", "integer", "real", "date", "datetime", "boolean"]
        for col_type in valid_types:
            col = ColumnDef(name="test", type=col_type)  # type: ignore[arg-type]
            assert col.type == col_type


class TestCreateTable:
    """Tests for CreateTable operation."""

    def test_creates_table_with_columns(self) -> None:
        """Creates a table with multiple columns."""
        op = CreateTable(
            table="people",
            columns=[
                ColumnDef(name="id", type="integer", nullable=False),
                ColumnDef(name="name", type="text"),
            ],
        )
        assert op.table == "people"
        assert len(op.columns) == 2

    def test_requires_at_least_one_column(self) -> None:
        """Rejects table with no columns."""
        with pytest.raises(ValueError):
            CreateTable(table="empty", columns=[])


class TestAddColumn:
    """Tests for AddColumn operation."""

    def test_creates_add_column_operation(self) -> None:
        """Creates an add column operation."""
        op = AddColumn(table="people", column="email", type="text")
        assert op.table == "people"
        assert op.column == "email"
        assert op.type == "text"
        assert op.nullable is True

    def test_add_non_nullable_column(self) -> None:
        """Creates a non-nullable add column operation."""
        op = AddColumn(
            table="people", column="required_field", type="text", nullable=False
        )
        assert op.nullable is False


class TestDropColumn:
    """Tests for DropColumn operation."""

    def test_creates_drop_column_operation(self) -> None:
        """Creates a drop column operation."""
        op = DropColumn(table="people", column="old_field")
        assert op.table == "people"
        assert op.column == "old_field"


class TestNameValidation:
    """Tests for table/column name validation."""

    def test_rejects_name_with_special_chars(self) -> None:
        """Rejects names containing special characters."""
        with pytest.raises(ValidationError, match="Invalid table name"):
            CreateTable(
                table="invalid-name",
                columns=[ColumnDef(name="id", type="integer")],
            )

    def test_rejects_name_starting_with_number(self) -> None:
        """Rejects names starting with a number."""
        with pytest.raises(ValidationError, match="Invalid table name"):
            CreateTable(
                table="123table",
                columns=[ColumnDef(name="id", type="integer")],
            )

    def test_rejects_column_name_with_spaces(self) -> None:
        """Rejects column names with spaces."""
        with pytest.raises(ValidationError, match="Invalid column name"):
            CreateTable(
                table="valid_table",
                columns=[ColumnDef(name="invalid name", type="text")],
            )

    def test_accepts_valid_names(self) -> None:
        """Accepts valid alphanumeric names with underscores."""
        op = CreateTable(
            table="user_profiles_2",
            columns=[
                ColumnDef(name="user_id", type="integer"),
                ColumnDef(name="_private", type="text"),
            ],
        )
        assert op.table == "user_profiles_2"

    def test_rejects_empty_name(self) -> None:
        """Rejects empty names."""
        with pytest.raises(ValidationError, match="name cannot be empty"):
            CreateTable(
                table="",
                columns=[ColumnDef(name="id", type="integer")],
            )

    def test_add_column_validates_table_name(self) -> None:
        """AddColumn validates table name."""
        with pytest.raises(ValidationError, match="Invalid table name"):
            AddColumn(table="bad-table", column="field", type="text")

    def test_add_column_validates_column_name(self) -> None:
        """AddColumn validates column name."""
        with pytest.raises(ValidationError, match="Invalid column name"):
            AddColumn(table="good_table", column="bad column", type="text")

    def test_drop_column_validates_names(self) -> None:
        """DropColumn validates both table and column names."""
        with pytest.raises(ValidationError, match="Invalid table name"):
            DropColumn(table="bad-table", column="field")
        with pytest.raises(ValidationError, match="Invalid column name"):
            DropColumn(table="good_table", column="bad-column")


class TestTranspile:
    """Tests for DDL transpilation."""

    def test_transpile_create_table(self) -> None:
        """Transpiles CreateTable to CREATE TABLE SQL."""
        op = CreateTable(
            table="people",
            columns=[
                ColumnDef(name="id", type="integer", nullable=False),
                ColumnDef(name="name", type="text"),
                ColumnDef(name="active", type="boolean"),
            ],
        )
        sql = transpile(op)
        assert sql == (
            "CREATE TABLE people (\n"
            "    id INTEGER NOT NULL,\n"
            "    name TEXT,\n"
            "    active BOOLEAN\n"
            ")"
        )

    def test_transpile_create_table_all_types(self) -> None:
        """Transpiles all column types correctly."""
        op = CreateTable(
            table="test",
            columns=[
                ColumnDef(name="col_text", type="text"),
                ColumnDef(name="col_integer", type="integer"),
                ColumnDef(name="col_real", type="real"),
                ColumnDef(name="col_date", type="date"),
                ColumnDef(name="col_datetime", type="datetime"),
                ColumnDef(name="col_boolean", type="boolean"),
            ],
        )
        sql = transpile(op)
        assert "col_text TEXT" in sql
        assert "col_integer INTEGER" in sql
        assert "col_real REAL" in sql
        assert "col_date DATE" in sql
        assert "col_datetime DATETIME" in sql
        assert "col_boolean BOOLEAN" in sql

    def test_transpile_add_column(self) -> None:
        """Transpiles AddColumn to ALTER TABLE SQL."""
        op = AddColumn(table="people", column="email", type="text")
        sql = transpile(op)
        assert sql == "ALTER TABLE people ADD COLUMN email TEXT"

    def test_transpile_add_non_nullable_column(self) -> None:
        """Transpiles non-nullable AddColumn correctly."""
        op = AddColumn(
            table="people", column="required", type="integer", nullable=False
        )
        sql = transpile(op)
        assert sql == "ALTER TABLE people ADD COLUMN required INTEGER NOT NULL"

    def test_transpile_drop_column(self) -> None:
        """Transpiles DropColumn to ALTER TABLE DROP COLUMN SQL."""
        op = DropColumn(table="people", column="old_field")
        sql = transpile(op)
        assert sql == "ALTER TABLE people DROP COLUMN old_field"


class TestExecute:
    """Tests for schema executor."""

    def test_execute_create_table(self) -> None:
        """Execute creates table in database."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            op = CreateTable(
                table="people",
                columns=[
                    ColumnDef(name="id", type="integer", nullable=False),
                    ColumnDef(name="name", type="text"),
                ],
            )
            execute(db, conn, op)

            schema = get_schema(conn)
            assert "people" in schema
            assert schema["people"].column_by_name("id") is not None
            assert schema["people"].column_by_name("name") is not None

    def test_execute_add_column(self) -> None:
        """Execute adds column to existing table."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            # First create table
            create_op = CreateTable(
                table="people",
                columns=[ColumnDef(name="id", type="integer")],
            )
            execute(db, conn, create_op)

            # Then add column
            add_op = AddColumn(table="people", column="email", type="text")
            execute(db, conn, add_op)

            schema = get_schema(conn)
            assert schema["people"].column_by_name("email") is not None

    def test_execute_drop_column(self) -> None:
        """Execute drops column from table."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            # First create table with two columns
            create_op = CreateTable(
                table="people",
                columns=[
                    ColumnDef(name="id", type="integer"),
                    ColumnDef(name="old_field", type="text"),
                ],
            )
            execute(db, conn, create_op)

            # Then drop column
            drop_op = DropColumn(table="people", column="old_field")
            execute(db, conn, drop_op)

            schema = get_schema(conn)
            assert schema["people"].column_by_name("old_field") is None
            assert schema["people"].column_by_name("id") is not None

    def test_execute_records_schema_op(self) -> None:
        """Execute records operation in _schema_ops table."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)
            op = CreateTable(
                table="people",
                columns=[ColumnDef(name="id", type="integer")],
            )
            execute(db, conn, op)

            cursor = conn.execute("SELECT op_type, op_json FROM _schema_ops")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "create_table"
            # Pydantic uses compact JSON without spaces
            assert '"table":"people"' in row[1]

    def test_execute_records_all_op_types(self) -> None:
        """Execute records correct op_type for each operation."""
        db = Database(":memory:")
        with db.connect() as conn:
            db.ensure_schema_ops(conn)

            # Create table
            create_op = CreateTable(
                table="test",
                columns=[ColumnDef(name="id", type="integer")],
            )
            execute(db, conn, create_op)

            # Add column
            add_op = AddColumn(table="test", column="field", type="text")
            execute(db, conn, add_op)

            # Drop column
            drop_op = DropColumn(table="test", column="field")
            execute(db, conn, drop_op)

            cursor = conn.execute("SELECT op_type FROM _schema_ops ORDER BY id")
            rows = cursor.fetchall()
            assert rows[0][0] == "create_table"
            assert rows[1][0] == "add_column"
            assert rows[2][0] == "drop_column"


class TestSchemaOpUnion:
    """Tests for SchemaOp union type."""

    def test_transpile_accepts_union_type(self) -> None:
        """Transpile accepts any SchemaOp union member."""
        ops: list[SchemaOp] = [
            CreateTable(table="t", columns=[ColumnDef(name="id", type="integer")]),
            AddColumn(table="t", column="f", type="text"),
            DropColumn(table="t", column="f"),
        ]
        for op in ops:
            sql = transpile(op)
            assert isinstance(sql, str)
            assert len(sql) > 0
