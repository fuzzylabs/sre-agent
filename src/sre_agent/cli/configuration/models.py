"""CLI configuration models."""

from pydantic import BaseModel, ConfigDict, Field


class AwsConfig(BaseModel):
    """AWS configuration values for CLI deployment."""

    region: str = "eu-west-2"
    profile: str | None = None


class EcsConfig(BaseModel):
    """ECS configuration values for CLI deployment."""

    project_name: str = "sre-agent"
    cluster_name: str = "sre-agent"
    task_family: str = "sre-agent"
    task_cpu: int = 512
    task_memory: int = 1024
    task_cpu_architecture: str = "X86_64"
    image_tag: str = "latest"
    ecr_repo_sre_agent: str = "sre-agent"
    ecr_repo_slack_mcp: str = "sre-agent-slack-mcp"
    secret_anthropic_name: str = "sre-agent/anthropic_api_key"
    secret_slack_bot_name: str = "sre-agent/slack_bot_token"
    secret_github_token_name: str = "sre-agent/github_token"
    log_group_name: str = "/ecs/sre-agent"
    slack_mcp_host: str = "127.0.0.1"
    slack_mcp_port: int = 13080


class IntegrationConfig(BaseModel):
    """Integration and provider configuration values."""

    model: str = "claude-sonnet-4-5-20250929"
    model_provider: str = "anthropic"
    notification_platform: str = "slack"
    code_repository_provider: str = "github"
    deployment_platform: str = "aws"
    logging_platform: str = "cloudwatch"
    slack_channel_id: str | None = None
    github_mcp_url: str = "https://api.githubcopilot.com/mcp/"


class DeploymentState(BaseModel):
    """Runtime deployment state discovered or created by the CLI."""

    vpc_id: str | None = None
    private_subnet_ids: list[str] = Field(default_factory=list)
    security_group_id: str | None = None
    secret_anthropic_arn: str | None = None
    secret_slack_bot_arn: str | None = None
    secret_github_token_arn: str | None = None
    exec_role_arn: str | None = None
    task_role_arn: str | None = None
    ecr_sre_agent_uri: str | None = None
    task_definition_arn: str | None = None
    cluster_arn: str | None = None


class CliConfig(BaseModel):
    """CLI configuration and deployment state."""

    model_config = ConfigDict(extra="ignore")

    aws: AwsConfig = Field(default_factory=AwsConfig)
    ecs: EcsConfig = Field(default_factory=EcsConfig)
    integrations: IntegrationConfig = Field(default_factory=IntegrationConfig)
    deployment: DeploymentState = Field(default_factory=DeploymentState)
