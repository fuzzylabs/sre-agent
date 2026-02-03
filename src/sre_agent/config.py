"""Configuration management for the SRE Agent."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AWSConfig(BaseSettings):
    """AWS configuration for CloudWatch access."""

    model_config = SettingsConfigDict(env_prefix="AWS_")

    region: str = Field(default="us-east-1", description="AWS region")
    access_key_id: str | None = Field(default=None, description="AWS access key ID")
    secret_access_key: str | None = Field(default=None, description="AWS secret access key")


class GitHubConfig(BaseSettings):
    """GitHub configuration for MCP server."""

    model_config = SettingsConfigDict(env_prefix="GITHUB_")

    personal_access_token: str = Field(default="", description="GitHub Personal Access Token")
    repository: str | None = Field(default=None, description="Default repository (owner/repo)")


class SlackConfig(BaseSettings):
    """Slack configuration for MCP server."""

    model_config = SettingsConfigDict(env_prefix="SLACK_")

    xoxb_token: str | None = Field(
        default=None, alias="SLACK_BOT_TOKEN", description="Slack Bot token (xoxb-...)"
    )
    team_id: str | None = Field(default=None, description="Slack Team/Workspace ID")
    default_channel: str = Field(default="#sre-agent", description="Default channel for alerts")


class AgentConfig(BaseSettings):
    """Main agent configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Provider
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    model: str = Field(default="anthropic:claude-sonnet-4-20250514", alias="MODEL")

    # Sub-configs (required)
    aws: AWSConfig
    github: GitHubConfig
    slack: SlackConfig


def get_config() -> AgentConfig:
    """Load and return the agent configuration."""
    return AgentConfig(
        aws=AWSConfig(),
        github=GitHubConfig(),
        slack=SlackConfig(),
    )
