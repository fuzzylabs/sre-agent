"""Schemas for the LLM server."""

from enum import StrEnum

from anthropic.types import (
    MessageParam,
    RedactedThinkingBlock,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)
from mcp.types import Tool
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Content = list[TextBlock | ToolUseBlock | ThinkingBlock | RedactedThinkingBlock]


class Provider(StrEnum):
    """An enum containing the different LLM providers supported."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    SELF_HOSTED = "self-hosted"
    MOCK = "mock"


class LLMSettings(BaseSettings):
    """The settings for the LLM provider."""

    model_config = SettingsConfigDict()

    provider: Provider = Field(
        description="The provider for LLM text generation, e.g., anthropic.",
        default=Provider.MOCK,
    )
    model: str = Field(description="The name of the model.", default="")
    max_tokens: int | None = Field(
        description="The maximum number of tokens for generation.", default=None
    )


class TextGenerationPayload(BaseModel):
    """The payload for the request."""

    messages: list[MessageParam]
    tools: list[Tool]
