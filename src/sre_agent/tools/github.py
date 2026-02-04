"""GitHub integration using MCP server via Streamable HTTP."""

import logging

from pydantic_ai.mcp import MCPServerStreamableHTTP

from sre_agent.config import AgentConfig

logger = logging.getLogger(__name__)


def create_github_mcp_toolset(config: AgentConfig) -> MCPServerStreamableHTTP:
    """Create GitHub MCP server toolset for pydantic-ai.

    Connects to an external GitHub MCP server via Streamable HTTP.
    """
    if not config.github.mcp_url:
        logger.warning("GITHUB_MCP_URL not set, GitHub tools will be unavailable")

    logger.info(f"Connecting to GitHub MCP server (Streamable HTTP) at {config.github.mcp_url}")

    # spellchecker:ignore-next-line
    headers = {"Authorization": f"Bearer {config.github.personal_access_token}"}

    return MCPServerStreamableHTTP(
        config.github.mcp_url,
        timeout=60,
        headers=headers,
    )
