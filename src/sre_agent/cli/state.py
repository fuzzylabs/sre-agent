"""CLI state helpers."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sre_agent.config.paths import cli_config_path


class ConfigError(RuntimeError):
    """Configuration related errors."""


class CliConfig(BaseModel):
    """CLI configuration for ECS deployment."""

    model_config = ConfigDict(extra="ignore")

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
    private_subnet_ids: list[str] = Field(default_factory=list)
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
    model_provider: str = "anthropic"
    notification_platform: str = "slack"
    code_repository_provider: str = "github"
    deployment_platform: str = "aws"
    logging_platform: str = "cloudwatch"
    slack_channel_id: str | None = None
    github_mcp_url: str = "https://api.githubcopilot.com/mcp/"
    log_group_name: str = "/ecs/sre-agent"

    slack_mcp_host: str = "127.0.0.1"
    slack_mcp_port: int = 13080


def load_config() -> CliConfig:
    """Load CLI configuration from disk.

    Returns:
        The loaded configuration object.
    """
    path = cli_config_path()
    if not path.exists():
        return CliConfig()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid configuration file: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError("Configuration file must contain a JSON object.")

    try:
        return CliConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration values: {exc}") from exc


def save_config(config: CliConfig) -> Path:
    """Save CLI configuration to disk.

    Args:
        config: Configuration object to save.

    Returns:
        The saved configuration file path.
    """
    path = cli_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path
