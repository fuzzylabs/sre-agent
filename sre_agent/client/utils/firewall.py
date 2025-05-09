"""Encapsulation of LlamaFirewall functionality."""
from llamafirewall import LlamaFirewall, ScanDecision, ToolMessage, UserMessage

from .logger import logger

# Initialise Llama Firewall to block malicious inputs and tool calls
llama_firewall = LlamaFirewall()


async def check_with_llama_firewall(
    content: str, is_tool: bool = False
) -> tuple[bool, str | None]:
    """Scan content with LlamaFirewall and return block status and reason.

    Args:
        content: The text to scan.
        is_tool: Whether it's tool-related (input/output).

    Returns:
        A tuple (is_blocked: bool, reason: Optional[str])
    """
    msg = ToolMessage(content=content) if is_tool else UserMessage(content=content)
    result = await llama_firewall.scan_async(msg)
    logger.debug(f"LlamaFirewal check result, {result}")
    if result.decision == ScanDecision.BLOCK:
        return True, f"Blocked by LlamaFirewall, {result.reason}"
    return False, None
