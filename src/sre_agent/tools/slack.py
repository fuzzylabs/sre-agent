"""Slack integration using MCP server."""

from pydantic_ai.mcp import MCPServerStdio

from sre_agent.config import AgentConfig


def create_slack_mcp_toolset(config: AgentConfig) -> MCPServerStdio:
    """Create Slack MCP server toolset for pydantic-ai.

    Args:
        config: Agent configuration with Slack token.

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
            f"SLACK_BOT_TOKEN={config.slack.xoxb_token}",
            "-e",
            f"SLACK_TEAM_ID={config.slack.team_id}",
            "mcp/slack",
        ],
        timeout=30,
    )
