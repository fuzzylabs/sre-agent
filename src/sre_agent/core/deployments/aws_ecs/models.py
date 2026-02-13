"""Data models for ECS deployment."""

from dataclasses import dataclass, field


@dataclass
class EcsDeploymentConfig:
    """Configuration for ECS deployment."""

    aws_region: str
    aws_profile: str | None
    project_name: str
    cluster_name: str
    task_family: str
    task_cpu: int
    task_memory: int
    task_cpu_architecture: str
    image_tag: str
    vpc_id: str | None
    private_subnet_ids: list[str]
    security_group_id: str | None
    ecr_repo_sre_agent: str
    ecr_repo_slack_mcp: str
    secret_anthropic_name: str
    secret_slack_bot_name: str
    secret_github_token_name: str
    secret_anthropic_arn: str | None
    secret_slack_bot_arn: str | None
    secret_github_token_arn: str | None
    exec_role_arn: str | None
    task_role_arn: str | None
    ecr_sre_agent_uri: str | None
    task_definition_arn: str | None
    cluster_arn: str | None
    model: str
    slack_channel_id: str | None
    github_mcp_url: str
    log_group_name: str
    slack_mcp_host: str
    slack_mcp_port: int


@dataclass
class SecurityGroupInfo:
    """Representation of a security group."""

    group_id: str
    name: str
    description: str


@dataclass
class NetworkSelection:
    """Selected network configuration."""

    vpc_id: str
    private_subnet_ids: list[str] = field(default_factory=list)
