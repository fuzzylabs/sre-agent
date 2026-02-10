"""Slack integration using korotovsky/slack-mcp-server."""

import logging

from pydantic_ai.mcp import MCPServerSSE
from pydantic_ai.toolsets import FilteredToolset

from sre_agent.core.config import AgentConfig

logger = logging.getLogger(__name__)

# Only these tools are allowed for the agent
ALLOWED_SLACK_TOOLS = {"conversations_add_message"}


def create_slack_mcp_toolset(config: AgentConfig) -> FilteredToolset:
    """Create Slack MCP server toolset for pydantic-ai.

    Connects to an external Slack MCP server via SSE.
    """
    if not config.slack.mcp_url:
        logger.warning("SLACK_MCP_URL not set, Slack tools will be unavailable")

    logger.info(f"Connecting to Slack MCP server at {config.slack.mcp_url}")

    # Increase timeout to 60s for SSE tools
    mcp_server = MCPServerSSE(config.slack.mcp_url, timeout=60)

    # Filter to only allowed tools
    return mcp_server.filtered(filter_func=lambda _ctx, tool: tool.name in ALLOWED_SLACK_TOOLS)
