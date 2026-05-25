"""LangGraph state model for Quorum."""

from typing import Literal

from pydantic import BaseModel, Field

from quorum.schemas.critique import ArbitrationResult, CritiqueResult
from quorum.schemas.plan import QueryPlan
from quorum.schemas.query import QueryResult, ValidatedQuery
from quorum.schemas.report import InsightReport


class AgentState(BaseModel):
    """Single source of truth for graph execution state."""

    question: str
    schema_context: str
    query_plan: QueryPlan | None = None
    current_step_index: int = 0
    validated_query: ValidatedQuery | None = None
    query_result: QueryResult | None = None
    critique_openai: CritiqueResult | None = None
    critique_gemini: CritiqueResult | None = None
    critique_deepseek: CritiqueResult | None = None
    arbitration: ArbitrationResult | None = None
    attempts: int = 0
    max_attempts: int = 3
    all_results: list[QueryResult] = Field(default_factory=list)
    insight_report: InsightReport | None = None
    error_message: str | None = None
    status: Literal["running", "complete", "failed"] = "running"
