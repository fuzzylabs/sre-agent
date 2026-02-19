"""Runtime settings for the SRE Agent."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from sre_agent.config.paths import env_path

ENV_FILE_PATH = str(env_path())


class AWSSettings(BaseSettings):
    """AWS configuration for CloudWatch access."""

    model_config = SettingsConfigDict(env_prefix="AWS_", env_file=ENV_FILE_PATH, extra="ignore")

    region: str = Field(default="eu-west-2", description="AWS region")
    access_key_id: str | None = Field(default=None, description="AWS Access Key ID")
    secret_access_key: str | None = Field(default=None, description="AWS Secret Access Key")
    session_token: str | None = Field(default=None, description="AWS Session Token")


class GitHubSettings(BaseSettings):
    """GitHub configuration for MCP server via SSE."""

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_",
        env_file=ENV_FILE_PATH,
        extra="ignore",
    )

    # Required: cannot be empty
    personal_access_token: str = Field(description="GitHub Personal Access Token")
    mcp_url: str = Field(description="URL of GitHub MCP server (SSE)")
    owner: str = Field(description="Default GitHub repository owner")
    repo: str = Field(description="Default GitHub repository name")
    ref: str = Field(description="Preferred GitHub ref (branch, tag, or SHA)")


class SlackSettings(BaseSettings):
    """Slack configuration for korotovsky/slack-mcp-server."""

    model_config = SettingsConfigDict(
        env_prefix="SLACK_",
        env_file=ENV_FILE_PATH,
        extra="ignore",
    )

    # Required: cannot be empty
    channel_id: str = Field(description="Slack channel ID (Cxxxxxxxxxx)")
    mcp_url: str = Field(description="URL of Slack MCP server (SSE)")


class AgentSettings(BaseSettings):
    """Main agent configuration."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Provider
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    model: str = Field(default="claude-sonnet-4-5-20250929", alias="MODEL")

    # Sub-configs (required)
    aws: AWSSettings
    github: GitHubSettings
    slack: SlackSettings


def get_settings() -> AgentSettings:
    """Load and return the agent configuration.

    The sub-configs are automatically populated from the environment
    thanks to pydantic-settings.
    """
    # We use type: ignore[call-arg] because mypy doesn't know BaseSettings
    # will populate these fields from the environment variables.
    return AgentSettings(
        aws=AWSSettings(),
        github=GitHubSettings(),  # type: ignore[call-arg]
        slack=SlackSettings(),  # type: ignore[call-arg]
    )
