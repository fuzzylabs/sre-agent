"""A module containing schemas for the prompt server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


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
    slack_channel_id: str = os.getenv("SLACK_CHANNEL_ID", "")
    profiles: list[str] = field(
        default_factory=lambda: [
            p.strip() for p in os.getenv("PROFILES", "").split(",") if p.strip()
        ]
    )

    def __post_init__(self) -> None:
        """A post-constructor method for the dataclass.

        Only validates required GitHub fields, as Slack fields are optional.
        """
        required_fields = ["organisation", "repo_name", "project_root"]
        for field_name in required_fields:
            attr = getattr(self, field_name)
            if not attr:
                msg = f"Environment variable {field_name.upper()} is not set."
                raise ValueError(msg)
