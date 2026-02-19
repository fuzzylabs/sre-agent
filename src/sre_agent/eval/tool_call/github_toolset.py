"""GitHub MCP toolset construction for tool call evaluation."""

import os
from typing import Any

import opik
from pydantic_ai.mcp import MCPServerStreamableHTTP


def build_github_toolset() -> MCPServerStreamableHTTP:
    """Build a real GitHub MCP toolset.

    Returns:
        A GitHub MCP toolset.
    """
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

    if not token:
        msg = (
            "Missing GitHub MCP configuration. "
            "Set GITHUB_PERSONAL_ACCESS_TOKEN before running tool-call eval."
        )
        raise RuntimeError(msg)

    # spellchecker:ignore-next-line
    headers = {"Authorization": f"Bearer {token}"}

    async def process_tool_call(
        _ctx: Any,
        call_tool: Any,
        name: str,
        args: dict[str, Any],
    ) -> Any:
        """Process a tool call.

        Args:
            _ctx: The context.
            call_tool: The call tool.
            name: The name of the tool.
            args: The arguments of the tool.

        Returns:
            The result of the tool call.
        """
        raw_args = args if isinstance(args, dict) else {}
        with opik.start_as_current_span(
            name=name,
            type="tool",
            input=raw_args,
            metadata={"provider": "github_mcp", "mocked": False},
        ):
            return await call_tool(name, raw_args)

    return MCPServerStreamableHTTP(
        "https://api.githubcopilot.com/mcp/",
        timeout=60,
        headers=headers,
        process_tool_call=process_tool_call,
    )
