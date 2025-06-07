"""A collection of clients for performing text generation."""

import os
from abc import ABC, abstractmethod
from typing import cast

from anthropic import Anthropic
from anthropic.types import (
    Message,
    TextBlock,
    ToolParam,
    Usage,
)
from anthropic.types.message_param import MessageParam
from google import genai
from google.genai import types
from mcp import Tool
from pydantic import BaseModel
from utils.logger import logger  # type: ignore
from utils.schemas import (  # type: ignore
    Content,
    LLMSettings,
    TextGenerationPayload,
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
            type="message",
            stop_reason="end_turn",
            usage=Usage(input_tokens=0, output_tokens=len(msg)),
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

    def cache_messages(self, messages: list[MessageParam]) -> list[MessageParam]:
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
        messages = self.cache_messages(payload.messages)

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

        return response


class OpenAIClient(BaseClient):
    """A client for performing text generation using the OpenAI client."""

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using the OpenAI API."""
        raise NotImplementedError


class GeminiClient(BaseClient):
    """A client for performing text generation using the Gemeni client."""

    def __init__(self, settings: LLMSettings = LLMSettings()) -> None:
        """The constructor for the Gemini client."""
        super().__init__(settings)
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using the Gemini API."""
        # tools = self.cache_tools(payload.tools)
        # messages = self.cache_messages(payload.messages)

        if not self.settings.max_tokens:
            raise ValueError("Max tokens configuration has not been set.")

        response = self.client.models.generate_content(
            model=self.settings.model,
            contents=payload.messages,
            config=types.GenerateContentConfig(
                tools=payload.tools,
                max_output_tokens=self.settings.max_tokens,
                temperature=0.1,
            ),
        )

        logger.info(
            f"Token usage - Input: {response.usage_metadata.prompt_token_count}, "
            f"Output: {response.usage_metadata.candidates_token_count}, "
            f"Cache: {response.usage_metadata.cached_content_token_count}, "
            f"Tools: {response.usage_metadata.tool_use_prompt_token_count}, "
            f"Total: {response.usage_metadata.total_token_count}"
        )

        return response


class SelfHostedClient(BaseClient):
    """A client for performing text generation using a self-hosted model."""

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using a self-hosted model."""
        raise NotImplementedError
