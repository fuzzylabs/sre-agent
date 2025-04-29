"""A server for making requests to an LLM."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from anthropic import Anthropic
from anthropic.types import (
    Message,
    TextBlock,
    TextBlockParam,
    ToolParam,
    Usage,
)
from dotenv import load_dotenv
from fastapi import FastAPI
from utils.logger import logger  # type: ignore
from utils.schemas import (  # type: ignore
    Content,
    LLMFunc,
    LLMSettings,
    Provider,
    TextGenerationPayload,
)

load_dotenv()


STATE: dict[str, LLMFunc | LLMSettings] = {}


def _dummy_model(settings: LLMSettings, payload: TextGenerationPayload) -> Message:
    msg = "This is a template response from a dummy model."
    content: Content = [TextBlock(text=msg, type="text")]
    return Message(
        id="0",
        model=settings.model,
        content=content,
        role="assistant",
        type="message",
        stop_reason="end_turn",
        usage=Usage(input_tokens=0, output_tokens=len(msg)),
    )


def _anthropic_model(settings: LLMSettings, payload: TextGenerationPayload) -> Message:
    tools: list[ToolParam] = [
        ToolParam(
            name=tool.name, description=tool.description, input_schema=tool.inputSchema
        )
        for tool in payload.tools
    ]

    tools[-1]["cache_control"] = {"type": "ephemeral"}

    messages = payload.messages

    if len(messages) > 1:
        messages[-1]["content"] = _convert_tool_result_to_text_blocks(
            cast(Content, messages[-1]["content"])
        )

    if not settings.max_tokens:
        raise ValueError("Max tokens configuration has not been set.")

    return Anthropic().messages.create(
        model=settings.model,
        max_tokens=settings.max_tokens,
        messages=messages,
        tools=tools,
    )


LLM_CLIENT_MAP: dict[Provider, LLMFunc] = {
    Provider.ANTHROPIC: _anthropic_model,
    Provider.MOCK: _dummy_model,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    """A context manager for the REST application.

    On start-up the application will establish an LLM function and settings.
    """
    STATE["settings"] = LLMSettings()

    STATE["client"] = LLM_CLIENT_MAP.get(
        cast(LLMSettings, STATE["settings"]).provider, _dummy_model
    )

    if STATE["client"] is None:
        raise ValueError(
            f"Unknown LLM provider. Supported providers are: {", ".join(Provider)}"
        )

    yield
    STATE.clear()


app = FastAPI(lifespan=lifespan)


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


@app.post("/generate")
def generate(payload: TextGenerationPayload) -> Message:
    """An endpoint for generating text from messages and tools."""
    logger.debug(payload)
    llm: LLMFunc = cast(LLMFunc, STATE["client"])
    response: Message = llm(cast(LLMSettings, STATE["settings"]), payload)

    if hasattr(response, "usage"):
        logger.info(
            f"Token usage - Input: {response.usage.input_tokens}, "
            f"Output: {response.usage.output_tokens}, "
            f"Cache Creation: {response.usage.cache_creation_input_tokens}, "
            f"Cache Read: {response.usage.cache_read_input_tokens}"
        )

    return response
