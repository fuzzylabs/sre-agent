"""Schemas for the LLM server."""

from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Provider(StrEnum):
    """An enum containing the different LLM providers supported."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
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
        description="The maximum number of tokens for generation.", default=10000
    )
    ollama_api_url: str = Field(
        description="The Ollama API URL for local LLM inference.",
        default="http://localhost:11434",
    )
