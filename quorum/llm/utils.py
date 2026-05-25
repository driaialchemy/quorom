"""Shared LLM utilities for parsing, validation, and error handling."""

import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


class LLMParseError(Exception):
    """Raised when LLM response cannot be parsed into expected Pydantic model."""

    def __init__(self, message: str, raw_response: str | None = None):
        super().__init__(message)
        self.raw_response = raw_response


class RateLimitError(Exception):
    """Raised when LLM provider rate limit is exceeded."""

    pass


def strip_json_fences(text: str) -> str:
    """Remove markdown code fences from LLM response.

    Handles common patterns:
    - ```json\n{...}\n```
    - ```\n{...}\n```
    - ```json{...}```

    Args:
        text: Raw LLM response text

    Returns:
        Text with markdown fences removed
    """
    # Remove leading/trailing whitespace
    text = text.strip()

    # Pattern to match code fences with optional language specifier
    # Matches: ```json or ``` at start, ``` at end
    fence_pattern = r"^```(?:json)?\s*\n?(.*?)\n?```$"
    match = re.match(fence_pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return text


def parse_response_model(text: str, response_model: type[T]) -> T:
    """Parse LLM response text into Pydantic model.

    Strips JSON fences and validates against the response model schema.
    Does NOT retry on failure - that responsibility belongs to the caller.

    Args:
        text: Raw LLM response text
        response_model: Pydantic model class to validate against

    Returns:
        Validated Pydantic model instance

    Raises:
        LLMParseError: If text cannot be parsed or validated
    """
    cleaned_text = strip_json_fences(text)

    try:
        return response_model.model_validate_json(cleaned_text)
    except ValidationError as e:
        error_msg = f"Pydantic validation failed: {e}"
        raise LLMParseError(error_msg, raw_response=text) from e
    except Exception as e:
        error_msg = f"JSON parsing failed: {e}"
        raise LLMParseError(error_msg, raw_response=text) from e


def build_retry_prompt(
    original_response: str,
    schema_name: str,
    validation_error: str,
) -> str:
    """Construct a retry prompt for LLM when initial parsing fails.

    Args:
        original_response: The invalid response from first attempt
        schema_name: Name of the Pydantic schema (e.g., "QueryPlan")
        validation_error: Error message from validation failure

    Returns:
        Formatted retry prompt instructing LLM to fix the response
    """
    return f"""Your previous response could not be parsed as valid JSON matching the {schema_name} schema.

Validation error:
{validation_error}

Your previous response:
{original_response}

Please provide a corrected response that:
1. Contains ONLY valid JSON (no markdown, no preamble, no explanation)
2. Exactly matches the {schema_name} schema structure
3. Includes all required fields
4. Uses correct data types for all fields

Output the corrected JSON now:"""
