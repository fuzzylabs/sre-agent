"""A collection of clients for performing text generation."""

from abc import ABC, abstractmethod
from typing import Any, cast

from anthropic import Anthropic
from anthropic.types import MessageParam as AnthropicMessageBlock
from anthropic.types import ToolParam
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
    """A client for performing text generation using the Gemeni client."""

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using the Gemini API."""
        raise NotImplementedError


class SelfHostedClient(BaseClient):
    """A client for performing text generation using a self-hosted model."""

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using a self-hosted model."""
        raise NotImplementedError
