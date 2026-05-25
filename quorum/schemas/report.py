"""Final insight report schema for Quorum."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from quorum.schemas.critique import ArbitrationResult
from quorum.schemas.query import QueryResult


class InsightReport(BaseModel):
    """Structured business-facing output from the Quorum workflow."""

    original_question: str
    executive_summary: str
    key_findings: list[str] = Field(default_factory=list)
    data_tables: list[QueryResult] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    ensemble_summary: list[ArbitrationResult] = Field(default_factory=list)
    total_attempts: int
    steps_executed: int
    models_used: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
