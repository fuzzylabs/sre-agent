"""GitHub integration using MCP server."""

from pydantic_ai.mcp import MCPServerStdio

from sre_agent.config import AgentConfig


def create_github_mcp_toolset(config: AgentConfig) -> MCPServerStdio:
    """Create GitHub MCP server toolset for pydantic-ai.

    Args:
        config: Agent configuration with GitHub token.

    Returns:
        MCPServerStdio instance for use as agent toolset.
    """
    return MCPServerStdio(
        "docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            f"GITHUB_PERSONAL_ACCESS_TOKEN={config.github.personal_access_token}",
            "ghcr.io/github/github-mcp-server",
        ],
        timeout=30,
    )
