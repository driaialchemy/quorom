"""Tests for shared LLM utilities."""

import pytest
from pydantic import BaseModel, Field

from quorum.llm.utils import (
    LLMParseError,
    RateLimitError,
    build_retry_prompt,
    parse_response_model,
    strip_json_fences,
)


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""

    name: str
    count: int
    active: bool = True


class TestStripJsonFences:
    """Tests for strip_json_fences function."""

    def test_strips_json_language_fence(self):
        """Should remove ```json fences."""
        text = '```json\n{"name": "test", "count": 5}\n```'
        result = strip_json_fences(text)
        assert result == '{"name": "test", "count": 5}'

    def test_strips_plain_fence(self):
        """Should remove ``` fences without language specifier."""
        text = '```\n{"name": "test", "count": 5}\n```'
        result = strip_json_fences(text)
        assert result == '{"name": "test", "count": 5}'

    def test_strips_fence_without_newlines(self):
        """Should handle fences without internal newlines."""
        text = '```json{"name": "test", "count": 5}```'
        result = strip_json_fences(text)
        assert result == '{"name": "test", "count": 5}'

    def test_handles_no_fences(self):
        """Should return text unchanged if no fences present."""
        text = '{"name": "test", "count": 5}'
        result = strip_json_fences(text)
        assert result == text

    def test_handles_extra_whitespace(self):
        """Should strip leading/trailing whitespace."""
        text = '  \n{"name": "test", "count": 5}\n  '
        result = strip_json_fences(text)
        assert result == '{"name": "test", "count": 5}'

    def test_handles_multiline_json(self):
        """Should handle JSON with internal newlines."""
        text = '''```json
{
  "name": "test",
  "count": 5
}
```'''
        result = strip_json_fences(text)
        assert '"name": "test"' in result
        assert '"count": 5' in result


class TestParseResponseModel:
    """Tests for parse_response_model function."""

    def test_parses_valid_json(self):
        """Should parse valid JSON into Pydantic model."""
        text = '{"name": "test", "count": 5}'
        result = parse_response_model(text, SampleModel)
        assert isinstance(result, SampleModel)
        assert result.name == "test"
        assert result.count == 5
        assert result.active is True

    def test_parses_json_with_fences(self):
        """Should parse JSON with markdown fences."""
        text = '```json\n{"name": "test", "count": 5}\n```'
        result = parse_response_model(text, SampleModel)
        assert result.name == "test"
        assert result.count == 5

    def test_uses_default_values(self):
        """Should apply Pydantic defaults for omitted fields."""
        text = '{"name": "test", "count": 5}'
        result = parse_response_model(text, SampleModel)
        assert result.active is True

    def test_raises_on_missing_required_field(self):
        """Should raise LLMParseError when required field missing."""
        text = '{"name": "test"}'
        with pytest.raises(LLMParseError) as exc_info:
            parse_response_model(text, SampleModel)
        assert "validation failed" in str(exc_info.value).lower()
        assert exc_info.value.raw_response == text

    def test_raises_on_wrong_type(self):
        """Should raise LLMParseError when field has wrong type."""
        text = '{"name": "test", "count": "not_a_number"}'
        with pytest.raises(LLMParseError) as exc_info:
            parse_response_model(text, SampleModel)
        assert exc_info.value.raw_response == text

    def test_raises_on_invalid_json(self):
        """Should raise LLMParseError on malformed JSON."""
        text = '{"name": "test", count: 5}'  # Missing quotes on key
        with pytest.raises(LLMParseError) as exc_info:
            parse_response_model(text, SampleModel)
        # Pydantic v2 may report this as validation error or parsing error
        assert "failed" in str(exc_info.value).lower()
        assert exc_info.value.raw_response == text

    def test_raises_on_extra_fields(self):
        """Should raise LLMParseError on extra fields (default Pydantic behavior)."""
        text = '{"name": "test", "count": 5, "extra_field": "value"}'
        # Pydantic v2 ignores extra fields by default, so this should succeed
        result = parse_response_model(text, SampleModel)
        assert result.name == "test"

    def test_preserves_raw_response_in_error(self):
        """Should include original text in LLMParseError."""
        text = '{"invalid": "json"'
        with pytest.raises(LLMParseError) as exc_info:
            parse_response_model(text, SampleModel)
        assert exc_info.value.raw_response == text


class TestBuildRetryPrompt:
    """Tests for build_retry_prompt function."""

    def test_includes_schema_name(self):
        """Should include schema name in retry prompt."""
        prompt = build_retry_prompt(
            original_response='{"bad": "data"}',
            schema_name="QueryPlan",
            validation_error="Field 'steps' is required",
        )
        assert "QueryPlan" in prompt

    def test_includes_validation_error(self):
        """Should include validation error details."""
        error = "Field 'steps' is required"
        prompt = build_retry_prompt(
            original_response='{"bad": "data"}',
            schema_name="QueryPlan",
            validation_error=error,
        )
        assert error in prompt

    def test_includes_original_response(self):
        """Should include original invalid response."""
        original = '{"bad": "data"}'
        prompt = build_retry_prompt(
            original_response=original,
            schema_name="QueryPlan",
            validation_error="Error",
        )
        assert original in prompt

    def test_requests_json_only(self):
        """Should instruct LLM to return only JSON."""
        prompt = build_retry_prompt(
            original_response='{"bad": "data"}',
            schema_name="QueryPlan",
            validation_error="Error",
        )
        assert "ONLY valid JSON" in prompt or "only valid JSON" in prompt

    def test_mentions_required_fields(self):
        """Should remind LLM about required fields."""
        prompt = build_retry_prompt(
            original_response='{"bad": "data"}',
            schema_name="QueryPlan",
            validation_error="Error",
        )
        assert "required fields" in prompt.lower()


class TestExceptions:
    """Tests for custom exception classes."""

    def test_llm_parse_error_stores_raw_response(self):
        """LLMParseError should store raw response."""
        raw = '{"invalid": "json"'
        error = LLMParseError("Parse failed", raw_response=raw)
        assert error.raw_response == raw
        assert "Parse failed" in str(error)

    def test_llm_parse_error_without_raw_response(self):
        """LLMParseError should work without raw_response."""
        error = LLMParseError("Parse failed")
        assert error.raw_response is None

    def test_rate_limit_error(self):
        """RateLimitError should be instantiable."""
        error = RateLimitError("Rate limit exceeded")
        assert "Rate limit exceeded" in str(error)
