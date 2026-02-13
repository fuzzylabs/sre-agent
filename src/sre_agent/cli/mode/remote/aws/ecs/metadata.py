"""Shared metadata helpers for AWS ECS remote deployment flows."""

from sre_agent.cli.configuration.models import CliConfig

STATUS_KEY_VPC = "VPC"
STATUS_KEY_PRIVATE_SUBNETS = "Private subnets"
STATUS_KEY_SECURITY_GROUP = "Security group"
STATUS_KEY_SECRETS = "Secrets"
STATUS_KEY_IAM_ROLES = "IAM roles"
STATUS_KEY_ECR_REPOSITORIES = "ECR repositories"
STATUS_KEY_LOG_GROUP = "Log group"
STATUS_KEY_TASK_DEFINITION = "Task definition"
STATUS_KEY_ECS_CLUSTER = "ECS cluster"


def secret_names(config: CliConfig) -> tuple[str, str, str]:
    """Return configured secret names.

    Args:
        config: CLI configuration values.

    Returns:
        Secret names for Anthropic, Slack, and GitHub.
    """
    return (
        config.ecs.secret_anthropic_name,
        config.ecs.secret_slack_bot_name,
        config.ecs.secret_github_token_name,
    )


def secret_arns(config: CliConfig) -> tuple[str | None, str | None, str | None]:
    """Return configured secret ARNs.

    Args:
        config: CLI configuration values.

    Returns:
        Secret ARNs for Anthropic, Slack, and GitHub.
    """
    return (
        config.deployment.secret_anthropic_arn,
        config.deployment.secret_slack_bot_arn,
        config.deployment.secret_github_token_arn,
    )


def joined_secret_names(config: CliConfig) -> str:
    """Return configured secret names as a comma-separated string.

    Args:
        config: CLI configuration values.

    Returns:
        Comma-separated secret names.
    """
    return ", ".join(secret_names(config))


def default_iam_role_names(config: CliConfig) -> tuple[str, str]:
    """Return default IAM role names for remote deployment.

    Args:
        config: CLI configuration values.

    Returns:
        Execution and task role names.
    """
    return (
        f"{config.ecs.project_name}-task-execution",
        f"{config.ecs.project_name}-task",
    )


def iam_role_targets(config: CliConfig) -> tuple[str, str]:
    """Return IAM role display targets (ARN when available).

    Args:
        config: CLI configuration values.

    Returns:
        Execution and task role targets.
    """
    default_execution, default_task = default_iam_role_names(config)
    return (
        config.deployment.exec_role_arn or default_execution,
        config.deployment.task_role_arn or default_task,
    )
