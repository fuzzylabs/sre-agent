"""A collection of clients for performing text generation."""

from abc import ABC, abstractmethod
from typing import cast

from anthropic import Anthropic
from anthropic.types import (
    Message,
    TextBlock,
    TextBlockParam,
    ToolParam,
    Usage,
)
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
    def _convert_tool_result_to_text_blocks(
        result: list[Content],
    ) -> list[TextBlockParam]:
        """Convert a tool result to a list of text blocks.

        Args:
            result: The result to convert to a list of text blocks.

        Returns:
            The list of text blocks.
        """
        blocks = []
        for content in list(result):
            if "text" in content:
                blocks.append(TextBlockParam(text=content["text"], type="text"))
            else:
                raise ValueError(f"Unsupported tool result type: {type(content)}")

        # Add cache control to the blocks
        blocks[-1]["cache_control"] = {"type": "ephemeral"}

        return blocks

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using the Anthropic API.

        This method implements prompt caching for the Anthropic API.
        """
        tools: list[ToolParam] = [
            ToolParam(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
            )
            for tool in payload.tools
        ]

        tools[-1]["cache_control"] = {"type": "ephemeral"}

        messages = payload.messages

        if len(messages) > 1:
            messages[-1]["content"] = self._convert_tool_result_to_text_blocks(
                cast(Content, messages[-1]["content"])
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

        return response


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
