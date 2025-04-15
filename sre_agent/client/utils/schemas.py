"""Schemas for the client."""

import os
from dataclasses import dataclass, fields
from enum import StrEnum

from mcp import ClientSession
from mcp.types import Tool

from .logger import logger


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


@dataclass(frozen=True)
class AuthConfig:
    """A config class containing authorisation environment variables."""

    slack_signing_secret: str = os.getenv("SLACK_SIGNING_SECRET", "")
    dev_bearer_token: str = os.getenv("DEV_BEARER_TOKEN", "")

    def __post_init__(self) -> None:
        """A post-constructor method for the dataclass."""
        for field in fields(self):
            attr = getattr(self, field.name)

            if not attr:
                msg = f"Environment variable {field.name} is not set."
                logger.error(msg)
                raise ValueError(msg)
