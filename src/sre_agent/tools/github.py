"""GitHub integration using MCP server via Docker (Stdio)."""

from pydantic_ai.mcp import MCPServerStdio

from sre_agent.config import AgentConfig


def create_github_mcp_toolset(config: AgentConfig) -> MCPServerStdio:
    """Create GitHub MCP server toolset for pydantic-ai.

    Spawns the GitHub MCP server as a subprocess using Docker.
    This is more reliable than the remote endpoint for local development.

    Args:
        config: Agent configuration with GitHub token.

    Returns:
        MCPServerStdio instance.
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
        timeout=60,  # Increase timeout for Docker startup
    )
