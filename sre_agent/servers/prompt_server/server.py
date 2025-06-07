"""A server containing a prompt to trigger the agent."""

from functools import lru_cache

from mcp.server.fastmcp import FastMCP
from utils.schemas import PromptServerConfig  # type: ignore

mcp = FastMCP("sre-agent-prompt")
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 3001


@lru_cache
def _get_prompt_server_config() -> PromptServerConfig:
    return PromptServerConfig()


@mcp.prompt()
def diagnose(service: str, slack_channel_id: str) -> str:
    """Prompt the agent to perform a task."""
    return f"""I have an error with my application, can you check the logs for the
{service} service, I only want you to check the pods logs, look up only the 1000
most recent logs. Feel free to scroll up until you find relevant errors that
contain reference to a file.

Once you have these errors and the file name, get the file contents of the path
{_get_prompt_server_config().project_root} for the repository
{_get_prompt_server_config().repo_name} in the organisation
{_get_prompt_server_config().organisation}. Keep listing the directories until you
find the file name and then get the contents of the file.

Please use the file contents to diagnose the error, then please create an issue in
GitHub reporting a fix for the issue. Once you have diagnosed the error and created an
issue please report this to the following Slack channel: {slack_channel_id}.

Please only do this ONCE, don't keep making issues or sending messages to Slack."""


if __name__ == "__main__":
    mcp.run()
