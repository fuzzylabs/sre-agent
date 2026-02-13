"""AWS ECS remote deployment status helpers for the CLI."""

from rich.table import Table

from sre_agent.cli.configuration.models import CliConfig
from sre_agent.cli.mode.remote.aws.ecs.metadata import (
    STATUS_KEY_ECR_REPOSITORIES,
    STATUS_KEY_ECS_CLUSTER,
    STATUS_KEY_IAM_ROLES,
    STATUS_KEY_LOG_GROUP,
    STATUS_KEY_PRIVATE_SUBNETS,
    STATUS_KEY_SECRETS,
    STATUS_KEY_SECURITY_GROUP,
    STATUS_KEY_TASK_DEFINITION,
    STATUS_KEY_VPC,
    iam_role_targets,
    joined_secret_names,
)
from sre_agent.cli.mode.remote.aws.ecs.steps import ecs_config_from_cli
from sre_agent.cli.presentation.console import console
from sre_agent.core.deployments.aws_ecs import check_deployment, create_session


def collect_deployment_status(config: CliConfig) -> dict[str, str]:
    """Collect live deployment status from AWS.

    Args:
        config: CLI configuration values.

    Returns:
        Deployment status values keyed by resource name.
    """
    ecs_config = ecs_config_from_cli(config)
    session = create_session(ecs_config)
    return check_deployment(session, ecs_config)


def print_deployment_status_table(config: CliConfig, results: dict[str, str]) -> None:
    """Print a deployment status table.

    Args:
        config: CLI configuration values.
        results: Deployment status values keyed by resource name.
    """
    targets = deployment_resource_targets(config)
    table = Table(title="Deployment resources", show_header=True, header_style="bold cyan")
    table.add_column("Resource", style="white", no_wrap=True)
    table.add_column("Name/ID", style="bright_white")
    table.add_column("Status", style="white", no_wrap=True)

    for name, status in results.items():
        table.add_row(name, targets.get(name, "-"), style_status(status))

    console.print(table)


def is_status_present(status: str) -> bool:
    """Return true when a resource status is healthy/present.

    Args:
        status: Resource status string.

    Returns:
        True when the status indicates a present resource.
    """
    return status.startswith("present")


def should_block_deploy(results: dict[str, str]) -> bool:
    """Return true when deploy should be blocked to avoid duplicates.

    Args:
        results: Deployment status values keyed by resource name.

    Returns:
        True when existing resources or uncertain statuses are present.
    """
    return any(
        status_indicates_existing_resource(resource, status) for resource, status in results.items()
    )


def status_indicates_existing_resource(resource: str, status: str) -> bool:
    """Return true when status implies existing/uncertain resources.

    Args:
        resource: Resource name.
        status: Resource status string.

    Returns:
        True when deploy should treat the resource as existing or uncertain.
    """
    if status == "not set":
        return False
    if status.startswith("missing"):
        return False
    if resource == STATUS_KEY_ECS_CLUSTER and status.strip().lower() == "status inactive":
        return False
    return (
        status.startswith("present") or status.startswith("status ") or status.startswith("error")
    )


def deployment_resource_targets(config: CliConfig) -> dict[str, str]:
    """Return display names and IDs for deployment resources.

    Args:
        config: CLI configuration values.

    Returns:
        Display labels keyed by resource name.
    """
    task_definition_name = config.ecs.task_family
    if config.deployment.task_definition_arn:
        task_definition_name = f"{config.ecs.task_family} ({config.deployment.task_definition_arn})"

    iam_targets = iam_role_targets(config)
    ecr_targets = [config.deployment.ecr_sre_agent_uri or config.ecs.ecr_repo_sre_agent]
    cluster_target = config.ecs.cluster_name
    if config.deployment.cluster_arn:
        cluster_target = f"{config.ecs.cluster_name} ({config.deployment.cluster_arn})"

    return {
        STATUS_KEY_VPC: config.deployment.vpc_id or "not set",
        STATUS_KEY_PRIVATE_SUBNETS: ", ".join(config.deployment.private_subnet_ids) or "not set",
        STATUS_KEY_SECURITY_GROUP: config.deployment.security_group_id or "not set",
        STATUS_KEY_SECRETS: joined_secret_names(config),
        STATUS_KEY_IAM_ROLES: ", ".join(iam_targets),
        STATUS_KEY_ECR_REPOSITORIES: ", ".join(ecr_targets),
        STATUS_KEY_LOG_GROUP: config.ecs.log_group_name,
        STATUS_KEY_TASK_DEFINITION: task_definition_name,
        STATUS_KEY_ECS_CLUSTER: cluster_target,
    }


def style_status(status: str) -> str:
    """Return colourised status text for terminal output.

    Args:
        status: Resource status string.

    Returns:
        Rich-marked status text.
    """
    if status.startswith("present"):
        return f"[green]{status}[/green]"
    if status == "not set":
        return "[yellow]not set[/yellow]"
    if status.startswith("missing"):
        return f"[red]{status}[/red]"
    if status.startswith("error"):
        return f"[red]{status}[/red]"
    if status.startswith("status "):
        return f"[yellow]{status}[/yellow]"
    return status
