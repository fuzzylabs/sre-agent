"""Schemas for the client."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from enum import StrEnum
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from _typeshed import DataclassInstance
from mcp import ClientSession
from mcp.types import Tool
from shared.logger import logger  # type: ignore[import-not-found]

DEFAULT_QUERY_TIMEOUT = 300

load_dotenv()


def _validate_fields(self: DataclassInstance) -> None:
    for config in fields(self):
        attr = getattr(self, config.name)

        if not attr:
            env_var = config.name.upper()

            # Provide helpful context for missing credentials
            if env_var == "DEV_BEARER_TOKEN":
                msg = (
                    f"Environment variable {env_var} is not set. "
                    "This is required for API authentication. "
                    "Run 'python setup_credentials.py --mode minimal' to configure."
                )
            elif env_var == "SLACK_CHANNEL_ID":
                msg = (
                    f"Environment variable {env_var} is not set. "
                    "This is required for Slack notifications. "
                    "Either configure Slack integration or use minimal mode."
                )
            else:
                msg = (
                    f"Environment variable {env_var} is not set. "
                    "Run 'python setup_credentials.py' to configure credentials."
                )

            logger.error(msg)
            raise ValueError(msg)


@dataclass
class ServerSession:
    """A dataclass to hold the session and tools for a server."""

    tools: list[Tool]
    session: ClientSession


class MCPServer(StrEnum):
    """The service names for the MCP servers."""

    SLACK = "slack"
    GITHUB = "github"
    KUBERNETES = "kubernetes"
    PROMPT = "prompt-server"


@dataclass(frozen=True)
class AuthConfig:
    """A config class containing authorisation environment variables."""

    slack_signing_secret: str = os.getenv("SLACK_SIGNING_SECRET", "")
    dev_bearer_token: str = os.getenv("DEV_BEARER_TOKEN", "")

    def __post_init__(self) -> None:
        """A post-constructor method for the dataclass."""
        _validate_fields(self)


@dataclass(frozen=True)
class ClientConfig:
    """A client config storing parsed env variables."""

    slack_channel_id: str = os.getenv("SLACK_CHANNEL_ID", "")
    tools: list[str] = field(
        default_factory=lambda: json.loads(os.getenv("TOOLS", "[]"))
    )
    model: str = os.getenv("LLM_MODEL", "claude-3-7-sonnet-latest")
    max_tokens: int = 1000
    max_tool_retries: int = 3
    query_timeout: int = int(
        os.getenv("QUERY_TIMEOUT", DEFAULT_QUERY_TIMEOUT) or DEFAULT_QUERY_TIMEOUT
    )
    services: list[str] = field(
        default_factory=lambda: json.loads(os.getenv("SERVICES", "[]"))
    )

    def __post_init__(self) -> None:
        """A post-constructor method for the dataclass."""
        _validate_fields(self)
