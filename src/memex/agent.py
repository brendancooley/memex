"""Memex agent with pydantic-ai integration.

Provides an LLM-powered interface to the memex database with tools for
schema modification and data querying.
"""

from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

from memex.context import build_system_prompt
from memex.db.connection import Database
from memex.db.introspection import get_schema
from memex.ops.query import Delete, Insert, Query, Update
from memex.ops.query import execute as query_execute
from memex.ops.schema import AddColumn, ColumnDef, CreateTable
from memex.ops.schema import execute as schema_execute

# Default model for production use
DEFAULT_MODEL = "anthropic:claude-sonnet-4-20250514"


@dataclass
class AgentDeps:
    """Dependencies for the memex agent.

    Attributes:
        db: Database instance for all operations.
    """

    db: Database


# Base system prompt for the memex agent
BASE_SYSTEM_PROMPT = """\
You are Memex, a personal knowledge assistant and thought partner. You help \
users build a coherent personal knowledge base—not just store fragments, but \
actively shape an ontology that grows with their needs.

## Philosophy

Writes are casual, reads are synthesized. Users jot fragments as they come. \
Your job is to be a collaborator—resolving ambiguity, proposing structure, \
and maintaining coherence across the knowledge base.

The schema is discovered, not designed. It emerges from what users actually \
track. Propose tables and columns as patterns emerge, always with the user's \
approval.

## Guidelines

- **Clarify ambiguity.** When input is incomplete or could mean multiple \
things, ask a brief clarifying question rather than guessing.
- **Infer from context.** When the answer is obvious from conversation \
context, infer it—but confirm when uncertain.
- **Propose schema thoughtfully.** When you see a new kind of entity, propose \
a table structure. Don't over-engineer upfront; let the schema grow as needed.
- **Suggest normalization.** If you notice inconsistent formats, offer to \
standardize them.
- **Surface data quality issues.** If you spot incomplete or conflicting \
information, mention it proactively.
- Be conversational but concise—ask at most one clarifying question at a time.
- When confident, act; when uncertain, ask.
- Never make up information that isn't in the database.
- Use the tools provided to interact with the database.

Current database schema:
"""


def create_agent(model: Model | str | None = None) -> Agent[AgentDeps, str]:
    """Create and configure the memex agent with all tools.

    Args:
        model: The model to use. Defaults to TestModel for safe testing.
            Pass DEFAULT_MODEL or a model string for production use.

    Returns:
        Configured pydantic-ai Agent instance.
    """
    # Use TestModel by default to avoid requiring API keys during testing
    effective_model: Model | str = model if model is not None else TestModel()

    agent: Agent[AgentDeps, str] = Agent(
        effective_model,
        deps_type=AgentDeps,
        output_type=str,
    )

    # Register dynamic system prompt
    @agent.system_prompt
    def build_dynamic_system_prompt(ctx: RunContext[AgentDeps]) -> str:
        """Build system prompt with current schema."""
        with ctx.deps.db.connect() as conn:
            ctx.deps.db.ensure_schema_ops(conn)
            schema = get_schema(conn)
        return build_system_prompt(BASE_SYSTEM_PROMPT, schema)

    # Register schema tools
    _register_create_table_tool(agent)
    _register_add_column_tool(agent)

    # Register query tools
    _register_query_tool(agent)
    _register_insert_tool(agent)
    _register_update_tool(agent)
    _register_delete_tool(agent)

    return agent


# =============================================================================
# Schema Tools
# =============================================================================


def _register_create_table_tool(agent: Agent[AgentDeps, str]) -> None:
    """Register the create_table tool with the agent."""

    @agent.tool
    def create_table(
        ctx: RunContext[AgentDeps],
        table: str,
        columns: list[dict[str, Any]],
    ) -> str:
        """Create a new table in the database.

        Args:
            ctx: Run context with dependencies.
            table: Name of the table to create.
            columns: List of column definitions with 'name', 'type', 'nullable'.

        Returns:
            Success message or error description.
        """
        try:
            column_defs = [
                ColumnDef(
                    name=col["name"],
                    type=col["type"],
                    nullable=col.get("nullable", True),
                )
                for col in columns
            ]
            op = CreateTable(table=table, columns=column_defs)

            with ctx.deps.db.connect() as conn:
                ctx.deps.db.ensure_schema_ops(conn)
                schema_execute(ctx.deps.db, conn, op)

            col_names = ", ".join(c["name"] for c in columns)
            return f"Success: Created table '{table}' with columns: {col_names}"
        except Exception as e:
            return f"Error creating table: {e}"


def _register_add_column_tool(agent: Agent[AgentDeps, str]) -> None:
    """Register the add_column tool with the agent."""

    @agent.tool
    def add_column(
        ctx: RunContext[AgentDeps],
        table: str,
        column: str,
        col_type: str,
        nullable: bool = True,
    ) -> str:
        """Add a column to an existing table.

        Args:
            ctx: Run context with dependencies.
            table: Name of the table to modify.
            column: Name of the new column.
            col_type: Type of the column (text, integer, real, date, datetime, boolean).
            nullable: Whether the column allows NULL values (default True).

        Returns:
            Success message or error description.
        """
        try:
            op = AddColumn(
                table=table,
                column=column,
                type=col_type,  # type: ignore[arg-type]
                nullable=nullable,
            )

            with ctx.deps.db.connect() as conn:
                ctx.deps.db.ensure_schema_ops(conn)
                schema_execute(ctx.deps.db, conn, op)

            return f"Success: Added column '{column}' to table '{table}'"
        except Exception as e:
            return f"Error adding column: {e}"


# =============================================================================
# Query Tools
# =============================================================================


def _register_query_tool(agent: Agent[AgentDeps, str]) -> None:
    """Register the query tool with the agent."""

    @agent.tool
    def query(
        ctx: RunContext[AgentDeps],
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Execute a SELECT query and return results.

        Args:
            ctx: Run context with dependencies.
            sql: SQL SELECT query string.
            params: Optional named parameters for the query.

        Returns:
            Query results as a formatted string, or error description.
        """
        try:
            op = Query(sql=sql, params=params or {})

            with ctx.deps.db.connect() as conn:
                rows = query_execute(conn, op)

            if not rows:
                return "No results found"

            # Format results as readable string
            result_lines = [str(row) for row in rows]
            return f"Results ({len(rows)} rows):\n" + "\n".join(result_lines)
        except Exception as e:
            return f"Error executing query: {e}"


def _register_insert_tool(agent: Agent[AgentDeps, str]) -> None:
    """Register the insert tool with the agent."""

    @agent.tool
    def insert(
        ctx: RunContext[AgentDeps],
        table: str,
        data: dict[str, Any],
    ) -> str:
        """Insert a row into a table.

        Args:
            ctx: Run context with dependencies.
            table: Name of the table.
            data: Column-value pairs to insert.

        Returns:
            Success message with row id, or error description.
        """
        try:
            op = Insert(table=table, data=data)

            with ctx.deps.db.connect() as conn:
                row_id = query_execute(conn, op)

            return f"Success: Inserted row with id {row_id} into '{table}'"
        except Exception as e:
            return f"Error inserting row: {e}"


def _register_update_tool(agent: Agent[AgentDeps, str]) -> None:
    """Register the update tool with the agent."""

    @agent.tool
    def update(
        ctx: RunContext[AgentDeps],
        table: str,
        row_id: int,
        data: dict[str, Any],
    ) -> str:
        """Update a row in a table.

        Args:
            ctx: Run context with dependencies.
            table: Name of the table.
            row_id: ID of the row to update.
            data: Column-value pairs to update.

        Returns:
            Success message or error description.
        """
        try:
            op = Update(table=table, id=row_id, data=data)

            with ctx.deps.db.connect() as conn:
                query_execute(conn, op)

            return f"Success: Updated row {row_id} in '{table}'"
        except Exception as e:
            return f"Error updating row: {e}"


def _register_delete_tool(agent: Agent[AgentDeps, str]) -> None:
    """Register the delete tool with the agent."""

    @agent.tool
    def delete(
        ctx: RunContext[AgentDeps],
        table: str,
        row_id: int,
    ) -> str:
        """Delete a row from a table.

        Args:
            ctx: Run context with dependencies.
            table: Name of the table.
            row_id: ID of the row to delete.

        Returns:
            Success message or error description.
        """
        try:
            op = Delete(table=table, id=row_id)

            with ctx.deps.db.connect() as conn:
                query_execute(conn, op)

            return f"Success: Deleted row {row_id} from '{table}'"
        except Exception as e:
            return f"Error deleting row: {e}"
