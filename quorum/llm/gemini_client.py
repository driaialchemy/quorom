"""Gemini LLM client - handles Gemini 3.1 Pro Preview only."""

from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from quorum.llm.utils import (
    LLMParseError,
    build_retry_prompt,
    parse_response_model,
)

T = TypeVar("T", bound=BaseModel)


class GeminiLLMClient:
    """Async LLM client using Google GenAI SDK for Gemini."""

    def __init__(
        self,
        api_key: str,
        max_output_tokens: int = 4096,
    ):
        """Initialize Gemini client.

        Args:
            api_key: Google API key
            max_output_tokens: Maximum tokens in response (default 4096)
        """
        self.client = genai.Client(api_key=api_key)
        self.max_output_tokens = max_output_tokens

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        model_string: str,
    ) -> T:
        """Call LLM with retry logic for parsing failures.

        Args:
            system_prompt: System instructions for the model
            user_prompt: User message/prompt
            response_model: Pydantic model to validate response against
            model_string: Model identifier (must be 'gemini-3.1-pro-preview')

        Returns:
            Validated Pydantic model instance

        Raises:
            LLMParseError: If response cannot be parsed after retry
        """
        # Build config with system instruction
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.max_output_tokens,
        )

        # First attempt
        response = await self.client.aio.models.generate_content(
            model=model_string,
            contents=user_prompt,
            config=config,
        )
        response_text = response.text

        try:
            return parse_response_model(response_text, response_model)
        except LLMParseError as e:
            # Retry once with correction prompt
            retry_prompt = build_retry_prompt(
                original_response=response_text,
                schema_name=response_model.__name__,
                validation_error=str(e),
            )

            # For retry, we need to build a conversation with the original response
            # Gemini uses a different message format for multi-turn conversations
            retry_contents = [
                types.Content(
                    role="user",
                    parts=[types.Part(text=user_prompt)],
                ),
                types.Content(
                    role="model",
                    parts=[types.Part(text=response_text)],
                ),
                types.Content(
                    role="user",
                    parts=[types.Part(text=retry_prompt)],
                ),
            ]

            # Second attempt
            retry_response = await self.client.aio.models.generate_content(
                model=model_string,
                contents=retry_contents,
                config=config,
            )
            retry_text = retry_response.text

            # Parse retry response (will raise LLMParseError if still fails)
            return parse_response_model(retry_text, response_model)
