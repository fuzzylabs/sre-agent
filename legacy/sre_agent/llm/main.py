"""A server for making requests to an LLM."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from dotenv import load_dotenv
from fastapi import FastAPI
from shared.logger import logger
from shared.schemas import Message, TextGenerationPayload
from utils.clients import (
    AnthropicClient,
    BaseClient,
    DummyClient,
    GeminiClient,
    OpenAIClient,
    SelfHostedClient,
)
from utils.schemas import (
    LLMSettings,
    Provider,
)

load_dotenv()


STATE: dict[str, BaseClient] = {}


def get_client(provider: Provider) -> BaseClient:
    """Get the appropriate client for the given provider."""
    if provider == Provider.ANTHROPIC:
        return AnthropicClient()
    elif provider == Provider.MOCK:
        return DummyClient()
    elif provider == Provider.OPENAI:
        return OpenAIClient()
    elif provider == Provider.GEMINI:
        return GeminiClient()
    elif provider == Provider.SELF_HOSTED:
        return SelfHostedClient()
    else:
        return DummyClient()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    """A context manager for the REST application.

    On start-up the application will establish an LLM function and settings.
    """
    # Debug: Log environment variables
    logger.info(f"PROVIDER env var: {os.getenv('PROVIDER', 'NOT SET')}")
    logger.info(f"MODEL env var: {os.getenv('MODEL', 'NOT SET')}")
    logger.info(
        f"ANTHROPIC_API_KEY env var: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}"
    )

    settings = LLMSettings()
    logger.info(f"LLMSettings provider: {settings.provider}")
    logger.info(f"LLMSettings model: {settings.model}")

    STATE["client"] = get_client(settings.provider)

    if STATE["client"] is None:
        raise ValueError(f"Unknown LLM provider. Supported providers are: {', '.join(Provider)}")

    yield
    STATE.clear()


app = FastAPI(lifespan=lifespan)


@app.post("/generate")
def generate(payload: TextGenerationPayload) -> Message:
    """An endpoint for generating text from messages and tools."""
    logger.debug(f"Payload: {payload}")

    return cast(Message, STATE["client"].generate(payload))


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Health check endpoint for the firewall."""
    return {"status": "healthy"}
