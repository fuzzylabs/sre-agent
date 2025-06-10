"""A collection of clients for performing text generation."""

from abc import ABC, abstractmethod
from typing import cast

from anthropic import Anthropic
from anthropic.types import MessageParam as AnthropicMessageBlock
from anthropic.types import TextBlock as AnthropicTextBlock
from anthropic.types import ToolParam
from anthropic.types import ToolUseBlock as AnthropicToolUseBlock
from mcp.types import Tool
from pydantic import BaseModel
from shared.logger import logger  # type: ignore
from shared.schemas import (  # type: ignore
    Content,
    Message,
    MessageBlock,
    TextBlock,
    TextGenerationPayload,
    ToolResultBlock,
    ToolUseBlock,
    Usage,
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
        result: list[Content],
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

    def _convert_mcp_types_to_anthropic_types(
        self, messages: list[MessageBlock]
    ) -> list[AnthropicMessageBlock]:
        """Convert MCP types to Anthropic types."""
        processed_messages: list[AnthropicMessageBlock] = []
        for message in messages:
            processed_message = {"role": message.role, "content": []}
            for content in message.content:
                if isinstance(content, ToolUseBlock):
                    processed_message["content"].append(
                        AnthropicToolUseBlock(
                            id=content.id,
                            name=content.name,
                            input=content.arguments,
                            type=content.type,
                        )
                    )
                elif isinstance(content, TextBlock):
                    processed_message["content"].append(
                        AnthropicTextBlock(type=content.type, text=content.text)
                    )
                elif isinstance(content, ToolResultBlock):
                    processed_message["content"].append(content)
                else:
                    raise TypeError(f"Unsupported content type: {type(content)}")
            processed_messages.append(cast(AnthropicMessageBlock, processed_message))
        return processed_messages

    def _convert_content_to_mcp_types(self, contents: list[Content]) -> Content:
        """Convert Anthropic content to MCP types."""
        processed_content: Content = []
        for content in contents:
            if isinstance(content, AnthropicToolUseBlock):
                processed_content.append(
                    ToolUseBlock(
                        id=content.id,
                        name=content.name,
                        arguments=content.input,
                    )
                )
            elif isinstance(content, AnthropicTextBlock):
                processed_content.append(
                    TextBlock(
                        text=content.text,
                    )
                )
            else:
                raise TypeError(
                    f"Unsupported content type: {type(content)}, "
                    f"keys: {content.keys()}"
                )
        return processed_content

    @staticmethod
    def cache_tools(tools: list[Tool]) -> list[ToolParam]:
        """A method for adding a cache block to tools."""
        cached_tools: list[ToolParam] = [
            ToolParam(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema,
            )
            for tool in tools
        ]

        cached_tools[-1]["cache_control"] = {"type": "ephemeral"}
        return cached_tools

    def cache_messages(
        self, messages: list[AnthropicMessageBlock]
    ) -> list[AnthropicMessageBlock]:
        """A method for adding a cache block to messages."""
        cached_messages = messages
        if len(messages) > 1:
            cached_messages[-1]["content"] = self._add_cache_to_final_block(
                cast(Content, messages[-1]["content"])
            )
        return cached_messages

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using the Anthropic API.

        This method implements prompt caching for the Anthropic API.
        """
        tools = self.cache_tools(payload.tools)
        messages = self.cache_messages(
            self._convert_mcp_types_to_anthropic_types(payload.messages)
        )

        if not self.settings.max_tokens:
            raise ValueError("Max tokens configuration has not been set.")

        response = self.client.messages.create(
            model=self.settings.model,
            max_tokens=self.settings.max_tokens,
            messages=messages,
            tools=tools,
        )

        logger.info(
            f"Token usage - Input: {response.usage.input_tokens}, "
            f"Output: {response.usage.output_tokens}, "
            f"Cache Creation: {response.usage.cache_creation_input_tokens}, "
            f"Cache Read: {response.usage.cache_read_input_tokens}"
        )

        return Message(
            id=response.id,
            model=response.model,
            content=self._convert_content_to_mcp_types(response.content),
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
