"""OpenAI LLM client - handles GPT-5.5 only."""

from typing import TypeVar

import openai
from pydantic import BaseModel

from quorum.llm.utils import (
    LLMParseError,
    build_retry_prompt,
    parse_response_model,
)

T = TypeVar("T", bound=BaseModel)


class OpenAILLMClient:
    """Async LLM client using OpenAI SDK for GPT-5.5."""

    def __init__(
        self,
        api_key: str,
        max_tokens: int = 4096,
    ):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            max_tokens: Maximum tokens in response (default 4096)
        """
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.max_tokens = max_tokens

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
            model_string: Model identifier (must be 'gpt-5.5-2026-04-23')

        Returns:
            Validated Pydantic model instance

        Raises:
            LLMParseError: If response cannot be parsed after retry
        """
        # Build message list with system and user messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # First attempt - always use reasoning_effort="high" for critic work
        response = await self.client.chat.completions.create(
            model=model_string,
            messages=messages,
            max_tokens=self.max_tokens,
            reasoning_effort="high",
        )
        response_text = response.choices[0].message.content

        try:
            return parse_response_model(response_text, response_model)
        except LLMParseError as e:
            # Retry once with correction prompt
            retry_prompt = build_retry_prompt(
                original_response=response_text,
                schema_name=response_model.__name__,
                validation_error=str(e),
            )

            # Update messages for retry
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": retry_prompt})

            # Second attempt
            retry_response = await self.client.chat.completions.create(
                model=model_string,
                messages=messages,
                max_tokens=self.max_tokens,
                reasoning_effort="high",
            )
            retry_text = retry_response.choices[0].message.content

            # Parse retry response (will raise LLMParseError if still fails)
            return parse_response_model(retry_text, response_model)
