"""GitHub integration using GitHub's remote MCP server."""

from pydantic_ai.mcp import MCPServerStreamableHTTP

from sre_agent.config import AgentConfig

# GitHub's hosted MCP server URL
GITHUB_REMOTE_MCP_URL = "https://api.githubcopilot.com/mcp"


def create_github_mcp_toolset(config: AgentConfig) -> MCPServerStreamableHTTP:
    """Create GitHub MCP server toolset for pydantic-ai.

    Uses GitHub's hosted remote MCP server (no Docker needed).

    Args:
        config: Agent configuration with GitHub PAT.

    Returns:
        MCPServerStreamableHTTP instance.
    """
    return MCPServerStreamableHTTP(
        url=GITHUB_REMOTE_MCP_URL,
        headers={
            # spellchecker:ignore-next-line
            "Authorization": f"Bearer {config.github.personal_access_token}"
        },
    )
