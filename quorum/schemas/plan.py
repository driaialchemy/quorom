"""Planning schemas for Quorum."""

from pydantic import BaseModel, Field, model_validator


class QueryStep(BaseModel):
    """One planned data retrieval step."""

    step_number: int
    objective: str
    tables_required: list[str] = Field(default_factory=list)
    expected_columns: list[str] = Field(default_factory=list)
    expected_output_description: str


class QueryPlan(BaseModel):
    """Ordered plan for answering the user's question."""

    original_question: str
    reasoning: str
    steps: list[QueryStep] = Field(default_factory=list)
    total_steps: int

    @model_validator(mode="after")
    def total_steps_matches_steps(self) -> "QueryPlan":
        if self.total_steps != len(self.steps):
            raise ValueError("total_steps must equal len(steps)")
        return self
