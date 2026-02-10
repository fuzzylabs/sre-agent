"""CLI configuration helpers."""

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

APP_NAME = "sre-agent"
CONFIG_FILENAME = "config.json"


class ConfigError(RuntimeError):
    """Configuration related errors."""


@dataclass
class CliConfig:
    """CLI configuration for ECS deployment."""

    aws_region: str = "eu-west-2"
    aws_profile: str | None = None

    project_name: str = "sre-agent"
    cluster_name: str = "sre-agent"
    task_family: str = "sre-agent"
    task_cpu: int = 512
    task_memory: int = 1024
    task_cpu_architecture: str = "X86_64"
    image_tag: str = "latest"

    vpc_id: str | None = None
    private_subnet_ids: list[str] = field(default_factory=list)
    security_group_id: str | None = None

    ecr_repo_sre_agent: str = "sre-agent"
    ecr_repo_slack_mcp: str = "sre-agent-slack-mcp"

    secret_anthropic_name: str = "sre-agent/anthropic_api_key"
    secret_slack_bot_name: str = "sre-agent/slack_bot_token"
    secret_github_token_name: str = "sre-agent/github_token"
    secret_anthropic_arn: str | None = None
    secret_slack_bot_arn: str | None = None
    secret_github_token_arn: str | None = None

    exec_role_arn: str | None = None
    task_role_arn: str | None = None

    ecr_sre_agent_uri: str | None = None

    task_definition_arn: str | None = None
    cluster_arn: str | None = None

    model: str = "claude-sonnet-4-5-20250929"
    slack_channel_id: str | None = None
    github_mcp_url: str = "https://api.githubcopilot.com/mcp/"
    log_group_name: str = "/ecs/sre-agent"
    api_idle_timeout_seconds: int = 300

    slack_mcp_host: str = "127.0.0.1"
    slack_mcp_port: int = 13080


def config_dir() -> Path:
    """Return the user configuration directory.

    Returns:
        The user configuration directory path.
    """
    return Path(user_config_dir(APP_NAME))


def config_path() -> Path:
    """Return the configuration file path.

    Returns:
        The configuration file path.
    """
    return config_dir() / CONFIG_FILENAME


def load_config() -> CliConfig:
    """Load CLI configuration from disk.

    Returns:
        The loaded configuration object.
    """
    path = config_path()
    if not path.exists():
        return CliConfig()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid configuration file: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError("Configuration file must contain a JSON object.")

    return _config_from_dict(data)


def save_config(config: CliConfig) -> Path:
    """Save CLI configuration to disk.

    Args:
        config: Configuration object to save.

    Returns:
        The saved configuration file path.
    """
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    return path


def _config_from_dict(data: dict[str, Any]) -> CliConfig:
    """Build a CLI configuration from a dictionary.

    Args:
        data: Dictionary containing configuration data.

    Returns:
        The configuration object.
    """
    allowed_fields = {field.name for field in fields(CliConfig)}
    filtered: dict[str, Any] = {key: value for key, value in data.items() if key in allowed_fields}

    subnet_ids = filtered.get("private_subnet_ids")
    if isinstance(subnet_ids, str):
        filtered["private_subnet_ids"] = [
            item.strip() for item in subnet_ids.split(",") if item.strip()
        ]

    return CliConfig(**filtered)
