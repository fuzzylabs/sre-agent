"""A server for making requests to an LLM."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from anthropic.types import (
    Message,
)
from dotenv import load_dotenv
from fastapi import FastAPI
from utils.clients import (  # type: ignore
    AnthropicClient,
    BaseClient,
    DummyClient,
    GeminiClient,
    OpenAIClient,
    SelfHostedClient,
)
from utils.logger import logger  # type: ignore
from utils.schemas import (  # type: ignore
    LLMSettings,
    Provider,
    TextGenerationPayload,
)

load_dotenv()


STATE: dict[str, BaseClient] = {}


LLM_CLIENT_MAP: dict[Provider, BaseClient] = {
    Provider.ANTHROPIC: AnthropicClient(),
    Provider.MOCK: DummyClient(),
    Provider.OPENAI: OpenAIClient(),
    Provider.GEMINI: GeminiClient(),
    Provider.SELF_HOSTED: SelfHostedClient(),
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    """A context manager for the REST application.

    On start-up the application will establish an LLM function and settings.
    """
    STATE["client"] = LLM_CLIENT_MAP.get(LLMSettings().provider, DummyClient())

    if STATE["client"] is None:
        raise ValueError(
            f"Unknown LLM provider. Supported providers are: {", ".join(Provider)}"
        )

    yield
    STATE.clear()


app = FastAPI(lifespan=lifespan)


@app.post("/generate")
def generate(payload: TextGenerationPayload) -> Message:
    """An endpoint for generating text from messages and tools."""
    logger.debug(payload)
    llm = STATE["client"]
    response: Message = llm.generate(payload)

    if hasattr(response, "usage"):
        logger.info(
            f"Token usage - Input: {response.usage.input_tokens}, "
            f"Output: {response.usage.output_tokens}, "
            f"Cache Creation: {response.usage.cache_creation_input_tokens}, "
            f"Cache Read: {response.usage.cache_read_input_tokens}"
        )

    return response
