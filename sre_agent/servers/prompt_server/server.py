"""A server containing a prompt to trigger the agent."""

from functools import lru_cache

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from utils.schemas import PromptServerConfig

mcp = FastMCP("sre-agent-prompt")

mcp.settings.host = "127.0.0.1"  # nosec B104
mcp.settings.port = 3001


@lru_cache
def _get_prompt_server_config() -> PromptServerConfig:
    return PromptServerConfig()


def _is_slack_enabled() -> bool:
    """Check if Slack profile is enabled."""
    config = _get_prompt_server_config()
    return "slack" in config.profiles


@mcp.prompt()
def diagnose(service: str) -> str:
    """Prompt the agent to perform a task."""
    config = _get_prompt_server_config()

    base_prompt = f"""I have an error with my application, can you check the logs for the
{service} service, I only want you to check the pods logs, look up only the 1000
most recent logs. Feel free to scroll up until you find relevant errors that
contain reference to a file.

Once you have these errors and the file name, get the file contents of the path
{config.project_root} for the repository {config.repo_name} in the organisation
{config.organisation}. Keep listing the directories until you find the file name
and then get the contents of the file.

Please use the file contents to diagnose the error, then please create an issue in
GitHub reporting a fix for the issue using the `create_issue` tool.

When creating the GitHub issue, include both your diagnosis and the recommended fix in
the description, and tag the issue with the corresponding service name."""

    # Conditionally add Slack notification if enabled
    if _is_slack_enabled() and config.slack_channel_id:
        base_prompt += f"""

Once you have diagnosed the error and created an issue please report this to the
following Slack channel: {config.slack_channel_id}.

Always create the GitHub issue with your findings.

Please only do this ONCE. Don't keep making issues or sending messages to Slack."""
    else:
        base_prompt += """

Always create the GitHub issue with your findings.

Please only do this ONCE."""

    return base_prompt


app = FastAPI()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Health check endpoint for the firewall."""
    return {"status": "healthy"}


app.mount("/", mcp.sse_app())
