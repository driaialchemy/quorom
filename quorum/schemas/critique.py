"""Critique and arbitration schemas for Quorum."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CritiqueResult(BaseModel):
    """One model critic's evaluation of a query result."""

    critic_id: Literal["openai", "gemini", "deepseek"]
    step_number: int
    approved: bool
    confidence_score: float
    issues_found: list[str] = Field(default_factory=list)
    suggested_correction: str | None = None
    reasoning: str

    @field_validator("confidence_score")
    @classmethod
    def confidence_score_in_range(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return value


class ArbitrationResult(BaseModel):
    """Arbiter's final decision over all critic evaluations."""

    step_number: int
    final_approved: bool
    vote_summary: dict[str, bool] = Field(default_factory=dict)
    avg_confidence: float
    dissenting_critics: list[str] = Field(default_factory=list)
    disagreement_analysis: str
    merged_correction: str | None = None
    final_confidence: float
    arbitration_reasoning: str
