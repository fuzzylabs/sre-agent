"""A collection of clients for performing text generation."""

import json
import os
import requests
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


class OllamaClient(BaseClient):
    """A client for performing text generation using Ollama."""

    def __init__(self, settings: LLMSettings = LLMSettings()) -> None:
        """The constructor for the Ollama client."""
        super().__init__(settings)
        self.api_url = settings.ollama_api_url

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using the Ollama API."""
        try:
            # Convert the payload to Ollama format
            messages = self._convert_messages_to_ollama(payload.messages)
            
            # Prepare the request data
            request_data = {
                "model": self.settings.model,
                "messages": messages,
                "stream": False,
                "options": {}
            }
            
            # Add max_tokens if specified
            if self.settings.max_tokens:
                request_data["options"]["num_predict"] = self.settings.max_tokens
                
            # Add tools if present
            if payload.tools:
                request_data["tools"] = self._convert_tools_to_ollama(payload.tools)

            logger.debug(f"Ollama request: {request_data}")

            # Make the request to Ollama
            response = requests.post(
                f"{self.api_url}/api/chat",
                json=request_data,
                timeout=120,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            ollama_response = response.json()
            logger.debug(f"Ollama response: {ollama_response}")

            # Convert response back to our format
            content: Content = [TextBlock(
                text=ollama_response.get("message", {}).get("content", ""),
                type="text"
            )]

            # Extract usage information if available
            usage = None
            if "usage" in ollama_response:
                usage_data = ollama_response["usage"]
                usage = Usage(
                    input_tokens=usage_data.get("prompt_tokens", 0),
                    output_tokens=usage_data.get("completion_tokens", 0),
                    cache_creation_input_tokens=None,
                    cache_read_input_tokens=None,
                )

            logger.info(
                f"Ollama token usage - Input: {usage.input_tokens if usage else 'N/A'}, "
                f"Output: {usage.output_tokens if usage else 'N/A'}"
            )

            return Message(
                id=f"ollama_{hash(str(ollama_response))}",
                model=self.settings.model,
                content=content,
                role="assistant",
                stop_reason="end_turn",
                usage=usage,
            )

        except requests.RequestException as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise ValueError(f"Ollama API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Ollama client: {e}")
            raise

    def _convert_messages_to_ollama(self, messages: list[Any]) -> list[dict[str, Any]]:
        """Convert messages to Ollama format."""
        ollama_messages = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Handle different content types
            if isinstance(content, list):
                # Extract text from content blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = "\n".join(text_parts)
            
            ollama_messages.append({
                "role": role,
                "content": str(content)
            })
        
        return ollama_messages

    def _convert_tools_to_ollama(self, tools: list[Any]) -> list[dict[str, Any]]:
        """Convert MCP tools to Ollama format."""
        ollama_tools = []
        
        for tool in tools:
            # Convert MCP tool format to Ollama function calling format
            if isinstance(tool, dict) and "function" in tool:
                ollama_tools.append({
                    "type": "function",
                    "function": tool["function"]
                })
        
        return ollama_tools


class SelfHostedClient(BaseClient):
    """A client for performing text generation using a self-hosted model."""

    def generate(self, payload: TextGenerationPayload) -> Message:
        """A method for generating text using a self-hosted model."""
        raise NotImplementedError
