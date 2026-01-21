"""Tests for context builder module."""

from memex.context import build_system_prompt, format_schema_summary
from memex.db.introspection import ColumnInfo, TableInfo


class TestFormatSchemaSummary:
    """Tests for format_schema_summary function."""

    def test_empty_schema_returns_empty_tables_section(self) -> None:
        """Empty schema produces 'Tables:' with '(none)' indicator."""
        schema: dict[str, TableInfo] = {}
        result = format_schema_summary(schema)
        assert result == "Tables:\n(none)"

    def test_single_table_format(self) -> None:
        """Single table is formatted with column names."""
        schema = {
            "person": TableInfo(
                name="person",
                columns=[
                    ColumnInfo(name="id", type="INTEGER", primary_key=True),
                    ColumnInfo(name="name", type="TEXT"),
                    ColumnInfo(name="address", type="TEXT"),
                    ColumnInfo(name="met_date", type="TEXT"),
                ],
            )
        }
        result = format_schema_summary(schema)
        expected = "Tables:\n- person (id, name, address, met_date)"
        assert result == expected

    def test_multiple_tables_sorted_alphabetically(self) -> None:
        """Multiple tables are sorted alphabetically."""
        schema = {
            "event": TableInfo(
                name="event",
                columns=[
                    ColumnInfo(name="id", type="INTEGER", primary_key=True),
                    ColumnInfo(name="title", type="TEXT"),
                    ColumnInfo(name="date", type="TEXT"),
                ],
            ),
            "person": TableInfo(
                name="person",
                columns=[
                    ColumnInfo(name="id", type="INTEGER", primary_key=True),
                    ColumnInfo(name="name", type="TEXT"),
                ],
            ),
        }
        result = format_schema_summary(schema)
        lines = result.split("\n")
        assert lines[0] == "Tables:"
        assert lines[1] == "- event (id, title, date)"
        assert lines[2] == "- person (id, name)"

    def test_table_with_no_columns(self) -> None:
        """Table with no columns shows empty parentheses."""
        schema = {"empty_table": TableInfo(name="empty_table", columns=[])}
        result = format_schema_summary(schema)
        assert result == "Tables:\n- empty_table ()"

    def test_preserves_column_order(self) -> None:
        """Column names appear in their original order."""
        schema = {
            "items": TableInfo(
                name="items",
                columns=[
                    ColumnInfo(name="z_col", type="TEXT"),
                    ColumnInfo(name="a_col", type="TEXT"),
                    ColumnInfo(name="m_col", type="TEXT"),
                ],
            )
        }
        result = format_schema_summary(schema)
        assert "- items (z_col, a_col, m_col)" in result


class TestBuildSystemPrompt:
    """Tests for build_system_prompt function."""

    def test_combines_base_instructions_and_schema(self) -> None:
        """System prompt combines base instructions with schema summary."""
        base_instructions = "You are a helpful assistant."
        schema = {
            "notes": TableInfo(
                name="notes",
                columns=[
                    ColumnInfo(name="id", type="INTEGER", primary_key=True),
                    ColumnInfo(name="content", type="TEXT"),
                ],
            )
        }
        result = build_system_prompt(base_instructions, schema)

        assert "You are a helpful assistant." in result
        assert "Tables:" in result
        assert "- notes (id, content)" in result

    def test_empty_schema_in_system_prompt(self) -> None:
        """System prompt handles empty schema gracefully."""
        base_instructions = "You are a helpful assistant."
        schema: dict[str, TableInfo] = {}
        result = build_system_prompt(base_instructions, schema)

        assert "You are a helpful assistant." in result
        assert "Tables:" in result
        assert "(none)" in result

    def test_schema_section_is_separated_from_base_instructions(self) -> None:
        """Schema section is clearly separated from base instructions."""
        base_instructions = "You are a helpful assistant."
        schema = {
            "users": TableInfo(
                name="users",
                columns=[ColumnInfo(name="id", type="INTEGER", primary_key=True)],
            )
        }
        result = build_system_prompt(base_instructions, schema)

        # Should have clear separation (double newline or similar)
        assert "\n\n" in result

    def test_multiline_base_instructions(self) -> None:
        """Handles multiline base instructions correctly."""
        base_instructions = """You are a helpful assistant.
You help users manage their knowledge.
Be concise and helpful."""
        schema = {
            "docs": TableInfo(
                name="docs",
                columns=[ColumnInfo(name="id", type="INTEGER", primary_key=True)],
            )
        }
        result = build_system_prompt(base_instructions, schema)

        assert "You are a helpful assistant." in result
        assert "You help users manage their knowledge." in result
        assert "Be concise and helpful." in result
        assert "- docs (id)" in result
