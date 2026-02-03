"""Slack integration using korotovsky/slack-mcp-server."""

from pydantic_ai.mcp import MCPServerSSE
from pydantic_ai.toolsets import FilteredToolset

from sre_agent.config import AgentConfig

# Only these tools are allowed for the agent
ALLOWED_SLACK_TOOLS = {"conversations_add_message"}


def create_slack_mcp_toolset(config: AgentConfig) -> FilteredToolset:
    """Create Slack MCP server toolset for pydantic-ai.

    Connects to an external Slack MCP server via SSE.
    The server must be started separately (e.g., via docker-compose).

    Only conversations_add_message is enabled for:
    1. Creating a thread when an error is detected
    2. Replying to the thread with the diagnosis (using thread_ts)

    Args:
        config: Agent configuration with Slack MCP URL.

    Returns:
        FilteredToolset with only allowed Slack tools.
    """
    mcp_server = MCPServerSSE(config.slack.mcp_url)

    # Filter to only allowed tools
    return mcp_server.filtered(filter_func=lambda _ctx, tool: tool.name in ALLOWED_SLACK_TOOLS)
