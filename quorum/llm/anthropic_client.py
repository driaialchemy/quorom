"""Anthropic LLM client - handles Claude and DeepSeek via Anthropic SDK."""

from typing import TypeVar

import anthropic
from pydantic import BaseModel

from quorum.llm.utils import (
    LLMParseError,
    build_retry_prompt,
    parse_response_model,
)

T = TypeVar("T", bound=BaseModel)


class AnthropicLLMClient:
    """Async LLM client using Anthropic SDK.

    Supports both Claude (standard endpoint) and DeepSeek (via Anthropic format).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        max_tokens: int = 4096,
    ):
        """Initialize Anthropic client.

        Args:
            api_key: API key for authentication
            base_url: Optional custom base URL (e.g., for DeepSeek)
            max_tokens: Maximum tokens in response (default 4096)
        """
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
        )
        self.max_tokens = max_tokens

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        model_string: str,
        enable_thinking: bool = False,
    ) -> T:
        """Call LLM with retry logic for parsing failures.

        Args:
            system_prompt: System instructions for the model
            user_prompt: User message/prompt
            response_model: Pydantic model to validate response against
            model_string: Model identifier (e.g., 'claude-sonnet-4-6', 'deepseek-v4-pro')
            enable_thinking: Enable extended thinking mode (for DeepSeek)

        Returns:
            Validated Pydantic model instance

        Raises:
            LLMParseError: If response cannot be parsed after retry
        """
        # Build message list
        messages = [{"role": "user", "content": user_prompt}]

        # Prepare API call kwargs
        api_kwargs = {
            "model": model_string,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": messages,
        }

        # Add thinking mode if enabled (for DeepSeek)
        # Note: budget_tokens is ignored by DeepSeek
        if enable_thinking:
            api_kwargs["thinking"] = {"type": "enabled"}

        # First attempt
        response = await self.client.messages.create(**api_kwargs)
        response_text = response.content[0].text

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

            api_kwargs["messages"] = messages

            # Second attempt
            retry_response = await self.client.messages.create(**api_kwargs)
            retry_text = retry_response.content[0].text

            # Parse retry response (will raise LLMParseError if still fails)
            return parse_response_model(retry_text, response_model)
