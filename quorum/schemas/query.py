"""SQL query and execution result schemas for Quorum."""

from typing import Any

from pydantic import BaseModel, Field


class ValidatedQuery(BaseModel):
    """SQL generated for a specific plan step."""

    step_number: int
    sql: str
    target_tables: list[str] = Field(default_factory=list)
    explanation: str
    estimated_row_limit: int
    critic_feedback: str | None = None


class QueryResult(BaseModel):
    """Snowflake execution result for a query."""

    step_number: int
    sql_executed: str
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int
    execution_time_ms: float
    success: bool
    error_detail: str | None = None
