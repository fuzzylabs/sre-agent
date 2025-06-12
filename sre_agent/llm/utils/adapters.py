"""Adapter classes to convert between different LLM API types and MCP types."""

from abc import ABC, abstractmethod
from typing import Any

from anthropic.types import MessageParam as AnthropicMessageBlock
from anthropic.types import TextBlock as AnthropicTextBlock
from anthropic.types import ToolParam
from anthropic.types import ToolResultBlockParam as AnthropicToolResultBlockParam
from anthropic.types import ToolUseBlock as AnthropicToolUseBlock
from shared.schemas import (  # type: ignore
    Content,
    TextBlock,
    TextGenerationPayload,
    ToolResultBlock,
    ToolUseBlock,
)


class LLMToMCPAdapter(ABC):
    """An abstract base class for adapting LLM responses to MCP types."""

    def __init__(self, contents: Any) -> None:
        """Initialize the adapter with LLM settings."""
        self.contents = contents

    @abstractmethod
    def adapt(self) -> Content:
        """Adapt the payload to MCP types."""
        pass


class AnthropicToMCPAdapter(LLMToMCPAdapter):
    """An adapter class to convert Anthropic content to MCP types."""

    def adapt(self) -> Content:
        """Convert Anthropic content to MCP types."""
        processed_content: Content = []
        for content in self.contents:
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


class LLMTextGenerationPayloadAdapter(ABC):
    """An abstract base class for adapting text generation payloads to LLM types."""

    def __init__(self, payload: TextGenerationPayload) -> None:
        """Initialize the adapter with a text generation payload."""
        self.payload = payload

    @abstractmethod
    def _adapt_messages(self) -> list[Any]:
        """Convert MCP message blocks to LLM message blocks."""
        pass

    @abstractmethod
    def _adapt_tools(self) -> list[Any]:
        """Convert MCP tools to LLM tools."""
        pass

    def adapt(self) -> tuple[list[Any], list[Any]]:
        """Adapt the payload to Gemini types."""
        messages = self._adapt_messages()
        tools = self._adapt_tools()
        return messages, tools


class AnthropicTextGenerationPayloadAdapter(LLMTextGenerationPayloadAdapter):
    """An adapter class to convert MCP text generation payloads to Anthropic types."""

    def _adapt_messages(self) -> list[AnthropicMessageBlock]:
        """Convert MCP types to Anthropic types."""
        processed_messages: list[AnthropicMessageBlock] = []
        for message in self.payload.messages:
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
                    processed_message["content"].append(
                        AnthropicToolResultBlockParam(
                            tool_use_id=content.tool_use_id,
                            content=content.content,
                            is_error=content.is_error,
                            type=content.type,
                        )
                    )
                else:
                    raise TypeError(f"Unsupported content type: {type(content)}")
            processed_messages.append(
                AnthropicMessageBlock(
                    content=processed_message["content"], role=processed_message["role"]
                )
            )
        return processed_messages

    def _adapt_tools(self) -> list[ToolParam]:
        """Convert MCP tools to Anthropic tools."""
        return [
            ToolParam(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema,
            )
            for tool in self.payload.tools
        ]
