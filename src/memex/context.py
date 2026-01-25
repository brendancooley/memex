"""Context builder for LLM system prompts.

Generates system prompts by combining base instructions with schema summaries
and other context information for the LLM interface.
"""

import datetime

from memex.db.introspection import TableInfo


def format_schema_summary(schema: dict[str, TableInfo]) -> str:
    """Generate a concise schema summary for LLM context.

    Takes introspection output and produces a human-readable text summary
    suitable for inclusion in system prompts.

    Args:
        schema: Dictionary mapping table names to TableInfo objects,
            as returned by memex.db.introspection.get_schema().

    Returns:
        Formatted schema summary. Example:
            Tables:
            - person (id, name, address, met_date)
            - event (id, title, date, notes)
    """
    lines = ["Tables:"]

    if not schema:
        lines.append("(none)")
        return "\n".join(lines)

    for table_name in sorted(schema.keys()):
        table = schema[table_name]
        column_names = [col.name for col in table.columns]
        columns_str = ", ".join(column_names)
        lines.append(f"- {table_name} ({columns_str})")

    return "\n".join(lines)


def build_system_prompt(
    base_instructions: str,
    schema: dict[str, TableInfo],
) -> str:
    """Build complete system prompt from components.

    Combines base instructions with schema summary and other context
    to produce a complete system prompt for the LLM.

    Args:
        base_instructions: Core instructions for the LLM (persona, rules, etc.).
        schema: Dictionary mapping table names to TableInfo objects.

    Returns:
        Complete system prompt string ready for LLM context.
    """
    schema_summary = format_schema_summary(schema)
    today = datetime.date.today().strftime("%B %d, %Y")
    return f"{base_instructions}\n\nToday's date: {today}\n\n{schema_summary}"
