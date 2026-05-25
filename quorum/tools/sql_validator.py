"""Deterministic SQL validation and safety enforcement.

This module validates and post-processes LLM-generated SQL before execution.
No LLM calls. No Snowflake calls. Pure deterministic safety checks.
"""

import re


class SQLValidationError(Exception):
    """Raised when SQL fails deterministic validation rules."""

    pass


def validate_and_fix_sql(sql: str) -> str:
    """Validate and fix SQL according to Quorum safety rules.

    Args:
        sql: Raw SQL string from LLM

    Returns:
        Validated and corrected SQL string

    Raises:
        SQLValidationError: If SQL violates safety rules

    Safety Rules:
        1. Must be a single SELECT statement
        2. No multi-statement SQL (multiple statements separated by semicolons)
        3. No fully qualified TPCH table names (e.g., SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS)
        4. Missing LIMIT gets LIMIT 50
        5. LIMIT above 100 is capped to 100
    """
    # Strip leading/trailing whitespace
    sql = sql.strip()

    if not sql:
        raise SQLValidationError("SQL is empty")

    # Remove trailing semicolon if present (common LLM behavior)
    if sql.endswith(";"):
        sql = sql[:-1].strip()

    # Check for multi-statement SQL (reject if multiple semicolons found)
    # This is a simple check - doesn't handle semicolons in strings perfectly,
    # but should catch obvious multi-statement attempts
    if ";" in sql:
        raise SQLValidationError(
            "Multi-statement SQL is not allowed. Only single SELECT statements are permitted."
        )

    # Must start with SELECT or WITH (for CTEs) - case-insensitive
    sql_upper = sql.upper()
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        raise SQLValidationError(
            "Only SELECT statements are allowed. SQL must start with SELECT or WITH (for CTEs)."
        )

    # Reject fully qualified TPCH table names
    # Pattern: SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.{table_name}
    # This should catch database.schema.table patterns
    qualified_pattern = r"\bSNOWFLAKE_SAMPLE_DATA\.TPCH_SF1\.\w+"
    if re.search(qualified_pattern, sql, re.IGNORECASE):
        raise SQLValidationError(
            "Fully qualified table names are not allowed. "
            "Use unqualified names (e.g., 'ORDERS' not 'SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS'). "
            "The session is already scoped to TPCH_SF1."
        )

    # Handle LIMIT clause
    sql = _enforce_limit_clause(sql)

    return sql


def _enforce_limit_clause(sql: str) -> str:
    """Enforce LIMIT clause rules: add if missing, cap if > 100.

    Args:
        sql: SQL string (already validated to be single SELECT)

    Returns:
        SQL with corrected LIMIT clause
    """
    # Pattern to match LIMIT clause (case-insensitive, handles whitespace and optional semicolon)
    # Captures: LIMIT <number>
    limit_pattern = r"\bLIMIT\s+(\d+)\s*$"

    match = re.search(limit_pattern, sql, re.IGNORECASE)

    if match:
        # LIMIT exists - check if it needs capping
        limit_value = int(match.group(1))

        if limit_value > 100:
            # Cap at 100
            sql = re.sub(limit_pattern, "LIMIT 100", sql, flags=re.IGNORECASE)

    else:
        # No LIMIT - append LIMIT 50
        sql = sql.rstrip() + " LIMIT 50"

    return sql
