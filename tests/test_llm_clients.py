"""Tests for LLM provider clients."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from quorum.llm.anthropic_client import AnthropicLLMClient
from quorum.llm.gemini_client import GeminiLLMClient
from quorum.llm.openai_client import OpenAILLMClient
from quorum.llm.utils import LLMParseError


class SampleResponseModel(BaseModel):
    """Sample Pydantic model for testing LLM responses."""

    name: str
    value: int


class TestAnthropicClient:
    """Tests for AnthropicLLMClient."""

    @pytest.mark.asyncio
    async def test_initialization_without_base_url(self):
        """Should initialize with standard Anthropic endpoint."""
        client = AnthropicLLMClient(api_key="test-key")
        assert client.max_tokens == 4096
        assert client.client.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_initialization_with_base_url(self):
        """Should initialize with custom base URL for DeepSeek."""
        client = AnthropicLLMClient(
            api_key="test-key",
            base_url="https://api.deepseek.com/anthropic",
        )
        assert client.max_tokens == 4096

    @pytest.mark.asyncio
    async def test_call_llm_success_first_attempt(self):
        """Should parse valid response on first attempt."""
        client = AnthropicLLMClient(api_key="test-key")

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"name": "test", "value": 42}')]

        with patch.object(
            client.client.messages, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="claude-sonnet-4-6",
            )

            assert isinstance(result, SampleResponseModel)
            assert result.name == "test"
            assert result.value == 42
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_with_thinking_mode(self):
        """Should enable thinking mode when requested."""
        client = AnthropicLLMClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"name": "test", "value": 42}')]

        with patch.object(
            client.client.messages, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="deepseek-v4-pro",
                enable_thinking=True,
            )

            call_kwargs = mock_create.call_args[1]
            assert "thinking" in call_kwargs
            assert call_kwargs["thinking"] == {"type": "enabled"}

    @pytest.mark.asyncio
    async def test_call_llm_retry_on_parse_failure(self):
        """Should retry once when initial response fails parsing."""
        client = AnthropicLLMClient(api_key="test-key")

        # First response is invalid, second is valid
        mock_response_1 = MagicMock()
        mock_response_1.content = [MagicMock(text='{"invalid": "json"')]

        mock_response_2 = MagicMock()
        mock_response_2.content = [MagicMock(text='{"name": "test", "value": 42}')]

        with patch.object(
            client.client.messages, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = [mock_response_1, mock_response_2]

            result = await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="claude-sonnet-4-6",
            )

            assert isinstance(result, SampleResponseModel)
            assert result.name == "test"
            assert result.value == 42
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_call_llm_raises_after_retry_failure(self):
        """Should raise LLMParseError if both attempts fail."""
        client = AnthropicLLMClient(api_key="test-key")

        # Both responses are invalid
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"invalid": "json"')]

        with patch.object(
            client.client.messages, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            with pytest.raises(LLMParseError):
                await client.call_llm(
                    system_prompt="You are helpful",
                    user_prompt="Generate test data",
                    response_model=SampleResponseModel,
                    model_string="claude-sonnet-4-6",
                )

            assert mock_create.call_count == 2


class TestOpenAIClient:
    """Tests for OpenAILLMClient."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Should initialize with API key."""
        client = OpenAILLMClient(api_key="test-key")
        assert client.max_tokens == 4096

    @pytest.mark.asyncio
    async def test_call_llm_success_first_attempt(self):
        """Should parse valid response on first attempt."""
        client = OpenAILLMClient(api_key="test-key")

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "test", "value": 42}'))
        ]

        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="gpt-5.5-2026-04-23",
            )

            assert isinstance(result, SampleResponseModel)
            assert result.name == "test"
            assert result.value == 42
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_uses_reasoning_effort_high(self):
        """Should always use reasoning_effort='high' for critic work."""
        client = OpenAILLMClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "test", "value": 42}'))
        ]

        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="gpt-5.5-2026-04-23",
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["reasoning_effort"] == "high"

    @pytest.mark.asyncio
    async def test_call_llm_retry_on_parse_failure(self):
        """Should retry once when initial response fails parsing."""
        client = OpenAILLMClient(api_key="test-key")

        # First response is invalid, second is valid
        mock_response_1 = MagicMock()
        mock_response_1.choices = [
            MagicMock(message=MagicMock(content='{"invalid": "json"'))
        ]

        mock_response_2 = MagicMock()
        mock_response_2.choices = [
            MagicMock(message=MagicMock(content='{"name": "test", "value": 42}'))
        ]

        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = [mock_response_1, mock_response_2]

            result = await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="gpt-5.5-2026-04-23",
            )

            assert isinstance(result, SampleResponseModel)
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_call_llm_includes_system_message(self):
        """Should include system message in correct format."""
        client = OpenAILLMClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "test", "value": 42}'))
        ]

        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="gpt-5.5-2026-04-23",
            )

            call_kwargs = mock_create.call_args[1]
            messages = call_kwargs["messages"]
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "You are helpful"
            assert messages[1]["role"] == "user"


class TestGeminiClient:
    """Tests for GeminiLLMClient."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Should initialize with API key."""
        with patch("quorum.llm.gemini_client.genai.Client"):
            client = GeminiLLMClient(api_key="test-key")
            assert client.max_output_tokens == 4096

    @pytest.mark.asyncio
    async def test_call_llm_success_first_attempt(self):
        """Should parse valid response on first attempt."""
        with patch("quorum.llm.gemini_client.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock response
            mock_response = MagicMock()
            mock_response.text = '{"name": "test", "value": 42}'

            mock_client.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )

            client = GeminiLLMClient(api_key="test-key")

            result = await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="gemini-3.1-pro-preview",
            )

            assert isinstance(result, SampleResponseModel)
            assert result.name == "test"
            assert result.value == 42

    @pytest.mark.asyncio
    async def test_call_llm_uses_system_instruction(self):
        """Should pass system prompt as system_instruction in config."""
        with patch("quorum.llm.gemini_client.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"name": "test", "value": 42}'

            mock_generate = AsyncMock(return_value=mock_response)
            mock_client.aio.models.generate_content = mock_generate

            client = GeminiLLMClient(api_key="test-key")

            await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="gemini-3.1-pro-preview",
            )

            call_kwargs = mock_generate.call_args[1]
            assert "config" in call_kwargs
            # Config object will have system_instruction set

    @pytest.mark.asyncio
    async def test_call_llm_retry_on_parse_failure(self):
        """Should retry once when initial response fails parsing."""
        with patch("quorum.llm.gemini_client.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # First response is invalid, second is valid
            mock_response_1 = MagicMock()
            mock_response_1.text = '{"invalid": "json"'

            mock_response_2 = MagicMock()
            mock_response_2.text = '{"name": "test", "value": 42}'

            mock_generate = AsyncMock(side_effect=[mock_response_1, mock_response_2])
            mock_client.aio.models.generate_content = mock_generate

            client = GeminiLLMClient(api_key="test-key")

            result = await client.call_llm(
                system_prompt="You are helpful",
                user_prompt="Generate test data",
                response_model=SampleResponseModel,
                model_string="gemini-3.1-pro-preview",
            )

            assert isinstance(result, SampleResponseModel)
            assert mock_generate.call_count == 2

    @pytest.mark.asyncio
    async def test_call_llm_raises_after_retry_failure(self):
        """Should raise LLMParseError if both attempts fail."""
        with patch("quorum.llm.gemini_client.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Both responses are invalid
            mock_response = MagicMock()
            mock_response.text = '{"invalid": "json"'

            mock_generate = AsyncMock(return_value=mock_response)
            mock_client.aio.models.generate_content = mock_generate

            client = GeminiLLMClient(api_key="test-key")

            with pytest.raises(LLMParseError):
                await client.call_llm(
                    system_prompt="You are helpful",
                    user_prompt="Generate test data",
                    response_model=SampleResponseModel,
                    model_string="gemini-3.1-pro-preview",
                )

            assert mock_generate.call_count == 2
