"""A collection of clients for performing text generation."""

import os
from abc import ABC, abstractmethod
from typing import Any, cast

from anthropic import Anthropic
from anthropic.types import MessageParam as AnthropicMessageBlock
from anthropic.types import ToolParam
from google import genai
from google.genai import types
from pydantic import BaseModel
from shared.logger import logger  # type: ignore
from shared.schemas import (  # type: ignore
    Content,
    Message,
    TextBlock,
    TextGenerationPayload,
    Usage,
)
from utils.adapters import (  # type: ignore[import-not-found]
    AnthropicTextGenerationPayloadAdapter,
    AnthropicToMCPAdapter,
    GeminiTextGenerationPayloadAdapter,
    GeminiToMCPAdapter,
)
from utils.schemas import (  # type: ignore
    LLMSettings,
)


class BaseClient(ABC):
    """A base client for LLM clients to implement."""

    def __init__(self, settings: LLMSettings = LLMSettings()) -> None:
        """The constructor for the base client."""
        self.settings = settings

    @abstractmethod
    def generate(self, payload: TextGenerationPayload) -> Message:
        """An abstract method for generating text using an LLM."""
        pass


class DummyClient(BaseClient):
    """A dummy client for mocking responses from an LLM."""

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A concrete generate method which returns a mocked response."""
        msg = "This is a template response from a dummy model."
        content: Content = [TextBlock(text=msg, type="text")]

        response = Message(
            id="0",
            model=self.settings.model,
            content=content,
            role="assistant",
            stop_reason="end_turn",
            usage=None,
        )

        logger.info(
            f"Token usage - Input: {response.usage.input_tokens}, "
            f"Output: {response.usage.output_tokens}, "
        )
        return response


class AnthropicClient(BaseClient):
    """A client for performing text generation using the Anthropic client."""

    def __init__(self, settings: LLMSettings = LLMSettings()) -> None:
        """The constructor for the Anthropic client."""
        super().__init__(settings)
        self.client = Anthropic()

    @staticmethod
    def _add_cache_to_final_block(
        result: Any,
    ) -> list[Content]:
        """Convert a tool result to a list of text blocks.

        Args:
            result: The result to convert to a list of text blocks.

        Returns:
            The list of text blocks.
        """
        blocks = []
        for content in list(result):
            if isinstance(content, BaseModel):
                blocks.append(content.model_dump())
            else:
                blocks.append(content)

        # Add cache control to the blocks
        blocks[-1]["cache_control"] = {"type": "ephemeral"}

        return cast(list[Content], blocks)

    @staticmethod
    def cache_tools(tools: list[ToolParam]) -> list[ToolParam]:
        """A method for adding a cache block to tools."""
        tools[-1]["cache_control"] = {"type": "ephemeral"}
        return tools

    def cache_messages(
        self, messages: list[AnthropicMessageBlock]
    ) -> list[AnthropicMessageBlock]:
        """A method for adding a cache block to messages."""
        cached_messages = messages
        if len(messages) > 1:
            cached_messages[-1]["content"] = self._add_cache_to_final_block(
                messages[-1]["content"]
            )
        return cached_messages

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using the Anthropic API.

        This method implements prompt caching for the Anthropic API.
        """
        adapter = AnthropicTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        cached_tools = self.cache_tools(tools)
        cached_messages = self.cache_messages(messages)

        if not self.settings.max_tokens:
            raise ValueError("Max tokens configuration has not been set.")

        response = self.client.messages.create(
            model=self.settings.model,
            max_tokens=self.settings.max_tokens,
            messages=cached_messages,
            tools=cached_tools,
        )

        logger.info(
            f"Token usage - Input: {response.usage.input_tokens}, "
            f"Output: {response.usage.output_tokens}, "
            f"Cache Creation: {response.usage.cache_creation_input_tokens}, "
            f"Cache Read: {response.usage.cache_read_input_tokens}"
        )

        adapter = AnthropicToMCPAdapter(response.content)
        content = adapter.adapt()

        return Message(
            id=response.id,
            model=response.model,
            content=content,
            role=response.role,
            stop_reason=response.stop_reason,
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_creation_input_tokens=response.usage.cache_creation_input_tokens,
                cache_read_input_tokens=response.usage.cache_read_input_tokens,
            ),
        )


class OpenAIClient(BaseClient):
    """A client for performing text generation using the OpenAI client."""

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using the OpenAI API."""
        raise NotImplementedError


class GeminiClient(BaseClient):
    """A client for performing text generation using the Gemini client."""

    def __init__(self, settings: LLMSettings = LLMSettings()) -> None:
        """The constructor for the Gemini client."""
        super().__init__(settings)
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using the Gemini API."""
        adapter = GeminiTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        if not self.settings.max_tokens:
            raise ValueError("Max tokens configuration has not been set.")

        response = self.client.models.generate_content(
            model=self.settings.model,
            contents=messages,
            config=types.GenerateContentConfig(
                tools=tools,
                max_output_tokens=self.settings.max_tokens,
            ),
        )

        if response.usage_metadata:
            logger.info(
                f"Token usage - Input: {response.usage_metadata.prompt_token_count}, "
                f"Output: {response.usage_metadata.candidates_token_count}, "
                f"Cache: {response.usage_metadata.cached_content_token_count}, "
                f"Tools: {response.usage_metadata.tool_use_prompt_token_count}, "
                f"Total: {response.usage_metadata.total_token_count}"
            )

        adapter = GeminiToMCPAdapter(response.candidates)
        content = adapter.adapt()

        return Message(
            id=response.response_id or f"gemini_{hash(str(response))}",
            model=response.model_version,
            content=content,
            role="assistant",
            stop_reason=response.candidates[0].finish_reason
            if response.candidates
            else "end_turn",
            usage=Usage(
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
                cache_creation_input_tokens=None,
                cache_read_input_tokens=response.usage_metadata.cached_content_token_count,
            )
            if response.usage_metadata
            else None,
        )


class SelfHostedClient(BaseClient):
    """A client for performing text generation using a self-hosted model."""

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using a self-hosted model."""
        raise NotImplementedError
