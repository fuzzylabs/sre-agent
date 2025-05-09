"""Encapsulation of LlamaFirewall functionality."""
from llamafirewall import (  # type: ignore
    LlamaFirewall,
    ScanDecision,
    ScanResult,
    ToolMessage,
    UserMessage,
)

from .logger import logger

# Initialise Llama Firewall to block malicious inputs and tool calls
llama_firewall = LlamaFirewall()


async def check_with_llama_firewall(
    content: str, is_tool: bool = False
) -> tuple[bool, ScanResult]:
    """Scan content with LlamaFirewall and return block status and reason.

    Args:
        content: The text to scan.
        is_tool: Whether it's tool-related (input/output).

    Returns:
        A tuple (is_blocked: bool, result: ScanResult)
    """
    msg = ToolMessage(content=content) if is_tool else UserMessage(content=content)
    result = await llama_firewall.scan_async(msg)
    logger.debug(f"LlamaFirewal check result, {result}")
    if result.decision == ScanDecision.BLOCK:
        return True, result
    return False, result
