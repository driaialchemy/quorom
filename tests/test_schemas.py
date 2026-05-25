"""Tests for Quorum Pydantic schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from quorum.schemas import (
    ArbitrationResult,
    CritiqueResult,
    InsightReport,
    QueryPlan,
    QueryResult,
    QueryStep,
    ValidatedQuery,
)
from quorum.state import AgentState


def make_query_result() -> QueryResult:
    return QueryResult(
        step_number=1,
        sql_executed="SELECT C_NAME FROM CUSTOMER LIMIT 10",
        columns=["C_NAME"],
        rows=[["Customer#000000001"]],
        row_count=1,
        execution_time_ms=12.5,
        success=True,
    )


def make_arbitration_result() -> ArbitrationResult:
    return ArbitrationResult(
        step_number=1,
        final_approved=True,
        vote_summary={"openai": True, "gemini": True, "deepseek": True},
        avg_confidence=0.91,
        dissenting_critics=[],
        disagreement_analysis="All critics agreed; shared assumptions may still miss semantic SQL issues.",
        final_confidence=0.9,
        arbitration_reasoning="The result answers the requested objective.",
    )


def test_query_step_defaults_list_fields() -> None:
    step = QueryStep(
        step_number=1,
        objective="Find top customers by revenue",
        expected_output_description="Ranked customer revenue table",
    )

    assert step.tables_required == []
    assert step.expected_columns == []


def test_query_plan_validates_total_steps() -> None:
    step = QueryStep(
        step_number=1,
        objective="Find top customers by revenue",
        tables_required=["CUSTOMER", "ORDERS"],
        expected_columns=["C_NAME", "TOTAL_REVENUE"],
        expected_output_description="Ranked customer revenue table",
    )

    plan = QueryPlan(
        original_question="Who are the top customers?",
        reasoning="One aggregate query can answer the question.",
        steps=[step],
        total_steps=1,
    )

    assert plan.total_steps == len(plan.steps)


def test_query_plan_rejects_total_step_mismatch() -> None:
    with pytest.raises(ValidationError):
        QueryPlan(
            original_question="Who are the top customers?",
            reasoning="One aggregate query can answer the question.",
            steps=[],
            total_steps=1,
        )


def test_validated_query_defaults_optional_feedback() -> None:
    query = ValidatedQuery(
        step_number=1,
        sql="SELECT C_NAME FROM CUSTOMER LIMIT 10",
        explanation="Returns sample customers.",
        estimated_row_limit=10,
    )

    assert query.target_tables == []
    assert query.critic_feedback is None


def test_query_result_defaults_error_detail() -> None:
    result = make_query_result()

    assert result.error_detail is None
    assert result.rows == [["Customer#000000001"]]


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_critique_result_rejects_confidence_outside_range(score: float) -> None:
    with pytest.raises(ValidationError):
        CritiqueResult(
            critic_id="openai",
            step_number=1,
            approved=False,
            confidence_score=score,
            issues_found=["Bad confidence"],
            reasoning="Confidence is outside the allowed range.",
        )


def test_critique_result_allows_confidence_range_edges() -> None:
    low = CritiqueResult(
        critic_id="gemini",
        step_number=1,
        approved=False,
        confidence_score=0.0,
        reasoning="No confidence.",
    )
    high = CritiqueResult(
        critic_id="deepseek",
        step_number=1,
        approved=True,
        confidence_score=1.0,
        reasoning="Full confidence.",
    )

    assert low.issues_found == []
    assert low.suggested_correction is None
    assert high.confidence_score == 1.0


def test_critique_result_rejects_unknown_critic_id() -> None:
    with pytest.raises(ValidationError):
        CritiqueResult(
            critic_id="claude",
            step_number=1,
            approved=True,
            confidence_score=0.8,
            reasoning="Unsupported critic id.",
        )


def test_arbitration_result_vote_summary_serializes() -> None:
    arbitration = make_arbitration_result()

    dumped = arbitration.model_dump()

    assert dumped["vote_summary"] == {
        "openai": True,
        "gemini": True,
        "deepseek": True,
    }
    assert arbitration.merged_correction is None


def test_insight_report_generated_at_auto_populates() -> None:
    report = InsightReport(
        original_question="Who are the top customers?",
        executive_summary="Customer#000000001 led the sample result.",
        key_findings=["Customer#000000001 appeared in the sample result."],
        data_tables=[make_query_result()],
        caveats=["Snowflake sample data."],
        ensemble_summary=[make_arbitration_result()],
        total_attempts=1,
        steps_executed=1,
        models_used=["claude-sonnet-4-6"],
    )

    assert isinstance(report.generated_at, datetime)
    assert report.generated_at.tzinfo is not None


def test_agent_state_defaults() -> None:
    state = AgentState(
        question="Who are the top customers?",
        schema_context="TPCH schema context",
    )

    assert state.query_plan is None
    assert state.current_step_index == 0
    assert state.validated_query is None
    assert state.query_result is None
    assert state.critique_openai is None
    assert state.critique_gemini is None
    assert state.critique_deepseek is None
    assert state.arbitration is None
    assert state.attempts == 0
    assert state.max_attempts == 3
    assert state.all_results == []
    assert state.insight_report is None
    assert state.error_message is None
    assert state.status == "running"


def test_agent_state_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        AgentState(
            question="Who are the top customers?",
            schema_context="TPCH schema context",
            status="paused",
        )


def test_required_fields_raise_validation_error() -> None:
    with pytest.raises(ValidationError):
        QueryStep(step_number=1, objective="Missing output description")

    with pytest.raises(ValidationError):
        QueryResult(
            step_number=1,
            row_count=1,
            execution_time_ms=1.0,
            success=True,
        )
