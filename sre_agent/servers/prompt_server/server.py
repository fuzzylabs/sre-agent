"""A server containing a prompt to trigger the agent."""

import os
from dataclasses import dataclass, fields
from functools import lru_cache
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

mcp = FastMCP("sre-agent-prompt")
mcp.settings.port = 3001

load_dotenv()


def _validate_fields(self: DataclassInstance) -> None:
    for config in fields(self):
        attr = getattr(self, config.name)

        if not attr:
            msg = f"Environment variable {config.name.upper()} is not set."
            raise ValueError(msg)


@dataclass(frozen=True)
class PromptServerConfig:
    """A config class containing Github org and repo name environment variables."""

    organisation: str = os.getenv("GITHUB_ORGANISATION", "")
    repo_name: str = os.getenv("GITHUB_REPO_NAME", "")
    project_root: str = os.getenv("PROJECT_ROOT", "")

    def __post_init__(self) -> None:
        """A post-constructor method for the dataclass."""
        _validate_fields(self)


@lru_cache
def _get_prompt_server_config() -> PromptServerConfig:
    return PromptServerConfig()


@mcp.prompt()
def diagnose(service: str, channel_id: str) -> str:
    """Prompt the agent to perform a task."""
    return f"""I have an error with my application, can you check the logs for the
    {service} service, I only want you to check the pods logs, look up only the 1000
    most recent logs. Feel free to scroll up until you find relevant errors that
    contain reference to a file, once you have these errors and the file name, get the
    file contents of the path {_get_prompt_server_config().project_root} for the
    repository {_get_prompt_server_config().repo_name} in the organisation
    {_get_prompt_server_config().organisation}. Keep listing the directories until you
    find the file name and then get the contents of the file. Once you have diagnosed
    the error please report this to the following slack channel: {channel_id}."""


if __name__ == "__main__":
    mcp.run()
