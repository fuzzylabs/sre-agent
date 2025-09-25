"""Encapsulation of LlamaFirewall functionality."""
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from llamafirewall import (
    LlamaFirewall,
    ScanDecision,
    ScanResult,
    ToolMessage,
    UserMessage,
)
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification
from transformers.models.auto.tokenization_auto import AutoTokenizer

STATE = {}


def load_models() -> None:
    """Asynchronously load the models for LlamaFirewall."""
    model_name = "meta-llama/Llama-Prompt-Guard-2-86M"

    if not os.environ.get("HF_HOME"):
        os.environ["HF_HOME"] = "~/.cache/huggingface"

    model_path = os.path.expanduser(
        os.path.join(os.environ["HF_HOME"], model_name.replace("/", "--"))
    )

    model = AutoModelForSequenceClassification.from_pretrained(model_name)  # type: ignore[no-untyped-call]
    model.save_pretrained(model_path)

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.save_pretrained(model_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for the FastAPI app.

    This function initializes the LlamaFirewall and yields control to the app.
    """
    load_models()

    STATE["llama_firewall"] = LlamaFirewall()

    yield
    STATE.clear()


app = FastAPI(lifespan=lifespan)


class FirewallPayload(BaseModel):
    """Payload for the firewall check.

    Attributes:
        content: The text to scan.
        is_tool: Whether it's tool-related (input/output).
    """

    content: str
    is_tool: bool = False


class FirewallResponse(BaseModel):
    """Result of the scan.

    Attributes:
        block: The decision made by the firewall whether to block communication.
        reason: The reason for the decision.
    """

    block: bool
    result: ScanResult


@app.post("/check")
async def check_with_llama_firewall(
    payload: FirewallPayload,
) -> FirewallResponse:
    """Scan content with LlamaFirewall and return block status and reason.

    Args:
        payload: The payload containing the content to scan and whether it's
            tool-related.

    Returns:
        FirewallResponse: The result of the scan, including block status and reason.
    """
    msg = (
        ToolMessage(content=payload.content)
        if payload.is_tool
        else UserMessage(content=payload.content)
    )
    result = await STATE["llama_firewall"].scan_async(msg)
    return FirewallResponse(block=result.decision == ScanDecision.BLOCK, result=result)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Health check endpoint for the firewall."""
    return {"status": "healthy"}
