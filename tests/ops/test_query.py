"""Tests for query operations with Pydantic models and executor."""

import sqlite3

import pytest

from memex.ops.query import (
    Delete,
    Insert,
    Query,
    Update,
    execute,
)


@pytest.fixture
def conn_with_table() -> sqlite3.Connection:
    """Create a connection with a test table."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT
        )
    """)
    conn.commit()
    return conn


class TestQueryModel:
    """Tests for Query model validation."""

    def test_query_accepts_select_statement(self) -> None:
        """Query model accepts SELECT statements."""
        query = Query(sql="SELECT * FROM users")
        assert query.sql == "SELECT * FROM users"

    def test_query_accepts_select_with_params(self) -> None:
        """Query model accepts SELECT with parameters."""
        query = Query(sql="SELECT * FROM users WHERE id = :id", params={"id": 1})
        assert query.params == {"id": 1}

    def test_query_rejects_non_select(self) -> None:
        """Query model rejects non-SELECT statements."""
        with pytest.raises(ValueError, match="must start with SELECT"):
            Query(sql="INSERT INTO users VALUES (1, 'test', 'test@test.com')")

    def test_query_rejects_delete(self) -> None:
        """Query model rejects DELETE statements."""
        with pytest.raises(ValueError, match="must start with SELECT"):
            Query(sql="DELETE FROM users WHERE id = 1")

    def test_query_rejects_update(self) -> None:
        """Query model rejects UPDATE statements."""
        with pytest.raises(ValueError, match="must start with SELECT"):
            Query(sql="UPDATE users SET name = 'test' WHERE id = 1")

    def test_query_rejects_drop(self) -> None:
        """Query model rejects DROP statements."""
        with pytest.raises(ValueError, match="must start with SELECT"):
            Query(sql="DROP TABLE users")

    def test_query_case_insensitive(self) -> None:
        """Query model accepts SELECT in any case."""
        query = Query(sql="select * from users")
        assert query.sql == "select * from users"


class TestInsertModel:
    """Tests for Insert model."""

    def test_insert_requires_table_and_data(self) -> None:
        """Insert model requires table and data."""
        insert = Insert(
            table="users", data={"name": "Alice", "email": "alice@test.com"}
        )
        assert insert.table == "users"
        assert insert.data == {"name": "Alice", "email": "alice@test.com"}


class TestUpdateModel:
    """Tests for Update model."""

    def test_update_requires_table_id_and_data(self) -> None:
        """Update model requires table, id, and data."""
        update = Update(table="users", id=1, data={"name": "Bob"})
        assert update.table == "users"
        assert update.id == 1
        assert update.data == {"name": "Bob"}


class TestDeleteModel:
    """Tests for Delete model."""

    def test_delete_requires_table_and_id(self) -> None:
        """Delete model requires table and id."""
        delete = Delete(table="users", id=1)
        assert delete.table == "users"
        assert delete.id == 1


class TestExecuteQuery:
    """Tests for executing Query operations."""

    def test_execute_query_returns_rows(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Query returns rows from database."""
        conn = conn_with_table
        conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", ("Alice", "alice@test.com")
        )
        conn.commit()

        query = Query(sql="SELECT name, email FROM users")
        result = execute(conn, query)

        assert result == [("Alice", "alice@test.com")]

    def test_execute_query_with_params(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Query with parameters."""
        conn = conn_with_table
        conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", ("Alice", "alice@test.com")
        )
        conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", ("Bob", "bob@test.com")
        )
        conn.commit()

        query = Query(
            sql="SELECT name FROM users WHERE name = :name", params={"name": "Bob"}
        )
        result = execute(conn, query)

        assert result == [("Bob",)]

    def test_execute_query_empty_result(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Query returns empty list when no rows match."""
        query = Query(sql="SELECT * FROM users")
        result = execute(conn_with_table, query)

        assert result == []


class TestExecuteInsert:
    """Tests for executing Insert operations."""

    def test_execute_insert_returns_row_id(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Insert returns the new row id."""
        insert = Insert(
            table="users", data={"name": "Alice", "email": "alice@test.com"}
        )
        row_id = execute(conn_with_table, insert)

        assert row_id == 1

    def test_execute_insert_creates_row(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Insert actually creates the row."""
        conn = conn_with_table
        insert = Insert(
            table="users", data={"name": "Alice", "email": "alice@test.com"}
        )
        execute(conn, insert)

        cursor = conn.execute("SELECT name, email FROM users WHERE id = 1")
        row = cursor.fetchone()

        assert row == ("Alice", "alice@test.com")

    def test_execute_insert_multiple_rows(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Insert returns sequential row ids."""
        conn = conn_with_table

        id1 = execute(conn, Insert(table="users", data={"name": "Alice"}))
        id2 = execute(conn, Insert(table="users", data={"name": "Bob"}))

        assert id1 == 1
        assert id2 == 2


class TestExecuteUpdate:
    """Tests for executing Update operations."""

    def test_execute_update_modifies_row(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Update modifies the specified row."""
        conn = conn_with_table
        conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", ("Alice", "old@test.com")
        )
        conn.commit()

        update = Update(table="users", id=1, data={"email": "new@test.com"})
        execute(conn, update)

        cursor = conn.execute("SELECT email FROM users WHERE id = 1")
        row = cursor.fetchone()

        assert row == ("new@test.com",)

    def test_execute_update_returns_none(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Update returns None on success."""
        conn = conn_with_table
        conn.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
        conn.commit()

        update = Update(table="users", id=1, data={"name": "Bob"})
        result = execute(conn, update)

        assert result is None

    def test_execute_update_raises_on_missing_row(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Update raises when row doesn't exist."""
        update = Update(table="users", id=999, data={"name": "Ghost"})

        with pytest.raises(ValueError, match="Row with id 999 not found"):
            execute(conn_with_table, update)


class TestExecuteDelete:
    """Tests for executing Delete operations."""

    def test_execute_delete_removes_row(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Delete removes the specified row."""
        conn = conn_with_table
        conn.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
        conn.commit()

        delete = Delete(table="users", id=1)
        execute(conn, delete)

        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE id = 1")
        count = cursor.fetchone()[0]

        assert count == 0

    def test_execute_delete_returns_none(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Delete returns None on success."""
        conn = conn_with_table
        conn.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
        conn.commit()

        delete = Delete(table="users", id=1)
        result = execute(conn, delete)

        assert result is None

    def test_execute_delete_raises_on_missing_row(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Execute Delete raises when row doesn't exist."""
        delete = Delete(table="users", id=999)

        with pytest.raises(ValueError, match="Row with id 999 not found"):
            execute(conn_with_table, delete)


class TestParameterizedQueriesPreventInjection:
    """Tests verifying parameterized queries prevent SQL injection."""

    def test_query_params_prevent_injection(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Query parameters are properly escaped, preventing injection."""
        conn = conn_with_table
        conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("Alice", "alice@test.com"),
        )
        conn.commit()

        # Attempt SQL injection via parameter
        malicious_name = "'; DROP TABLE users; --"
        query = Query(
            sql="SELECT * FROM users WHERE name = :name",
            params={"name": malicious_name},
        )
        result = execute(conn, query)

        # Should return empty result, not execute the injection
        assert result == []

        # Table should still exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone() is not None

    def test_insert_data_is_parameterized(
        self, conn_with_table: sqlite3.Connection
    ) -> None:
        """Insert data is parameterized, preventing injection."""
        conn = conn_with_table

        # Attempt SQL injection via insert data
        malicious_name = "'; DROP TABLE users; --"
        insert = Insert(table="users", data={"name": malicious_name})
        execute(conn, insert)

        # Table should still exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone() is not None

        # Malicious string should be stored literally
        cursor = conn.execute("SELECT name FROM users WHERE id = 1")
        row = cursor.fetchone()
        assert row[0] == malicious_name
