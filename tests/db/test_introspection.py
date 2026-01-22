"""Tests for database schema introspection."""

from memex.db.connection import Database
from memex.db.introspection import (
    ColumnInfo,
    TableInfo,
    get_schema,
)


class TestGetSchema:
    """Tests for get_schema function."""

    def test_empty_database_returns_empty_dict(self) -> None:
        """Empty database returns empty schema."""
        db = Database(":memory:")
        with db.connect() as conn:
            schema = get_schema(conn)
            assert schema == {}

    def test_single_table_introspection(self) -> None:
        """Introspects single table correctly."""
        db = Database(":memory:")
        with db.connect() as conn:
            conn.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT
                )
            """)
            schema = get_schema(conn)

            assert "users" in schema
            table = schema["users"]
            assert isinstance(table, TableInfo)
            assert table.name == "users"
            assert len(table.columns) == 3

    def test_column_info_extraction(self) -> None:
        """Extracts column info correctly."""
        db = Database(":memory:")
        with db.connect() as conn:
            conn.execute("""
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    price REAL,
                    active BOOLEAN DEFAULT 1
                )
            """)
            schema = get_schema(conn)
            columns = {col.name: col for col in schema["items"].columns}

            # Check id column
            assert columns["id"].name == "id"
            assert columns["id"].type == "INTEGER"
            assert columns["id"].primary_key is True

            # Check name column
            assert columns["name"].name == "name"
            assert columns["name"].type == "TEXT"
            assert columns["name"].nullable is False

            # Check price column
            assert columns["price"].name == "price"
            assert columns["price"].type == "REAL"
            assert columns["price"].nullable is True

            # Check active column with default
            assert columns["active"].name == "active"
            assert columns["active"].default_value == "1"

    def test_multiple_tables(self) -> None:
        """Introspects multiple tables."""
        db = Database(":memory:")
        with db.connect() as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER)")
            conn.execute("CREATE TABLE comments (id INTEGER PRIMARY KEY)")

            schema = get_schema(conn)

            assert len(schema) == 3
            assert "users" in schema
            assert "posts" in schema
            assert "comments" in schema

    def test_excludes_internal_tables(self) -> None:
        """Excludes SQLite internal tables and _schema_ops."""
        db = Database(":memory:")
        with db.connect() as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
            db.ensure_schema_ops(conn)  # Creates _schema_ops

            schema = get_schema(conn)

            # Should only have users, not _schema_ops or sqlite_* tables
            assert "users" in schema
            assert "_schema_ops" not in schema
            assert all(not name.startswith("sqlite_") for name in schema)

    def test_excludes_views(self) -> None:
        """get_schema only returns tables, not views."""
        db = Database(":memory:")
        with db.connect() as conn:
            conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
            conn.execute("CREATE VIEW active_users AS SELECT * FROM users")

            schema = get_schema(conn)

            assert "users" in schema
            assert "active_users" not in schema

    def test_table_name_with_space(self) -> None:
        """Introspects table with space in name."""
        db = Database(":memory:")
        with db.connect() as conn:
            conn.execute('CREATE TABLE "my table" (id INTEGER PRIMARY KEY, name TEXT)')

            schema = get_schema(conn)

            assert "my table" in schema
            table = schema["my table"]
            assert table.name == "my table"
            assert len(table.columns) == 2
            columns = {col.name: col for col in table.columns}
            assert columns["id"].primary_key is True
            assert columns["name"].type == "TEXT"

    def test_table_name_with_double_quote(self) -> None:
        """Introspects table with double quote in name."""
        db = Database(":memory:")
        with db.connect() as conn:
            # Table name with embedded double quote: " -> ""
            conn.execute(
                'CREATE TABLE "my""table" (id INTEGER PRIMARY KEY, value REAL)'
            )

            schema = get_schema(conn)

            assert 'my"table' in schema
            table = schema['my"table']
            assert table.name == 'my"table'
            assert len(table.columns) == 2
            columns = {col.name: col for col in table.columns}
            assert columns["id"].primary_key is True
            assert columns["value"].type == "REAL"


class TestTableInfo:
    """Tests for TableInfo dataclass."""

    def test_table_info_repr(self) -> None:
        """TableInfo has useful string representation."""
        table = TableInfo(
            name="users",
            columns=[
                ColumnInfo(name="id", type="INTEGER", nullable=False, primary_key=True),
                ColumnInfo(name="name", type="TEXT", nullable=False, primary_key=False),
            ],
        )
        repr_str = repr(table)
        assert "users" in repr_str
        assert "2 columns" in repr_str

    def test_column_by_name(self) -> None:
        """TableInfo.column_by_name() returns column or None."""
        table = TableInfo(
            name="users",
            columns=[
                ColumnInfo(name="id", type="INTEGER", nullable=False, primary_key=True),
                ColumnInfo(name="name", type="TEXT", nullable=False, primary_key=False),
            ],
        )

        id_col = table.column_by_name("id")
        assert id_col is not None
        assert id_col.name == "id"

        missing = table.column_by_name("nonexistent")
        assert missing is None


class TestColumnInfo:
    """Tests for ColumnInfo dataclass."""

    def test_column_info_defaults(self) -> None:
        """ColumnInfo has sensible defaults."""
        col = ColumnInfo(name="test", type="TEXT")
        assert col.nullable is True
        assert col.primary_key is False
        assert col.default_value is None

    def test_column_info_equality(self) -> None:
        """ColumnInfo equality works correctly."""
        col1 = ColumnInfo(name="id", type="INTEGER", primary_key=True)
        col2 = ColumnInfo(name="id", type="INTEGER", primary_key=True)
        col3 = ColumnInfo(name="name", type="TEXT")

        assert col1 == col2
        assert col1 != col3
