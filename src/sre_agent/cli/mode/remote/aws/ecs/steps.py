"""AWS ECS remote deployment step helpers for the CLI."""

from datetime import UTC, datetime

import questionary
from boto3.session import Session

from sre_agent.cli.env import load_env_values
from sre_agent.cli.mode.paths import project_root
from sre_agent.cli.mode.remote.aws.ecs.metadata import (
    default_iam_role_names,
    joined_secret_names,
    secret_arns,
)
from sre_agent.cli.state import CliConfig, save_config
from sre_agent.cli.ui import console
from sre_agent.core.deployments.aws_ecs import (
    EcsDeploymentConfig,
    ImageBuildConfig,
    NetworkSelection,
    SecurityGroupInfo,
    build_and_push_images,
    create_basic_vpc,
    create_secret,
    create_security_group,
    create_session,
    ensure_cluster,
    ensure_repository,
    ensure_roles,
    ensure_service_linked_role,
    get_secret_info,
    register_task_definition,
    restore_secret,
    run_task,
)
from sre_agent.core.deployments.aws_ecs import (
    wait_for_task_completion as wait_for_ecs_task_completion,
)


def ecs_config_from_cli(config: CliConfig) -> EcsDeploymentConfig:
    """Build an ECS deployment config from CLI config.

    Args:
        config: CLI configuration values.

    Returns:
        The ECS deployment configuration.
    """
    return EcsDeploymentConfig(
        aws_region=config.aws_region,
        aws_profile=config.aws_profile,
        project_name=config.project_name,
        cluster_name=config.cluster_name,
        task_family=config.task_family,
        task_cpu=config.task_cpu,
        task_memory=config.task_memory,
        task_cpu_architecture=config.task_cpu_architecture,
        image_tag=config.image_tag,
        vpc_id=config.vpc_id,
        private_subnet_ids=config.private_subnet_ids,
        security_group_id=config.security_group_id,
        ecr_repo_sre_agent=config.ecr_repo_sre_agent,
        ecr_repo_slack_mcp=config.ecr_repo_slack_mcp,
        secret_anthropic_name=config.secret_anthropic_name,
        secret_slack_bot_name=config.secret_slack_bot_name,
        secret_github_token_name=config.secret_github_token_name,
        secret_anthropic_arn=config.secret_anthropic_arn,
        secret_slack_bot_arn=config.secret_slack_bot_arn,
        secret_github_token_arn=config.secret_github_token_arn,
        exec_role_arn=config.exec_role_arn,
        task_role_arn=config.task_role_arn,
        ecr_sre_agent_uri=config.ecr_sre_agent_uri,
        task_definition_arn=config.task_definition_arn,
        cluster_arn=config.cluster_arn,
        model=config.model,
        slack_channel_id=config.slack_channel_id,
        github_mcp_url=config.github_mcp_url,
        log_group_name=config.log_group_name,
        slack_mcp_host=config.slack_mcp_host,
        slack_mcp_port=config.slack_mcp_port,
    )


def run_network_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Run the VPC selection step.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Starting ECS network setup...[/cyan]")
    console.print("[dim]This will create a new VPC, private subnet, and NAT gateway.[/dim]")
    session = create_session(ecs_config)
    report_step("Creating a new VPC with a private subnet and NAT gateway")
    network = create_basic_vpc(session, ecs_config.project_name, report_step)
    return _update_config_with_network(config, network)


def run_security_group_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Create a security group.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    if not config.vpc_id:
        console.print("[yellow]No VPC selected yet. Run network setup first.[/yellow]")
        return None

    console.print("[cyan]Setting up security group...[/cyan]")
    console.print("[dim]This will create a dedicated security group for ECS tasks.[/dim]")
    session = create_session(ecs_config)
    report_step("Creating a new security group for ECS tasks")
    suffix = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    name = f"{ecs_config.project_name}-tasks-{suffix}"
    description = "Security group for SRE Agent ECS tasks"
    group = create_security_group(session, config.vpc_id, name, description)
    return _update_config_with_security_group(config, group)


def run_secrets_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Create Secrets Manager entries for API keys.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Setting up Secrets Manager...[/cyan]")
    console.print("[dim]This stores API keys securely for ECS tasks.[/dim]")
    session = create_session(ecs_config)
    env_values = load_env_values()

    anthropic_arn = _ensure_secret(
        session,
        config.secret_anthropic_name,
        "Anthropic API key",
        config.secret_anthropic_arn,
        env_values.get("ANTHROPIC_API_KEY"),
    )
    if anthropic_arn is None:
        return None

    slack_arn = _ensure_secret(
        session,
        config.secret_slack_bot_name,
        "Slack bot token",
        config.secret_slack_bot_arn,
        env_values.get("SLACK_BOT_TOKEN"),
    )
    if slack_arn is None:
        return None

    github_arn = _ensure_secret(
        session,
        config.secret_github_token_name,
        "GitHub token",
        config.secret_github_token_arn,
        env_values.get("GITHUB_PERSONAL_ACCESS_TOKEN"),
    )
    if github_arn is None:
        return None

    return _update_config_with_secrets(config, anthropic_arn, slack_arn, github_arn)


def run_iam_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Create IAM roles for ECS tasks.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Setting up IAM roles...[/cyan]")
    console.print("[dim]This grants ECS tasks access to logs and secrets.[/dim]")

    configured_secret_arns = secret_arns(config)
    if any(secret is None for secret in configured_secret_arns):
        console.print("[yellow]Secrets are missing. Run the secrets step first.[/yellow]")
        return None

    session = create_session(ecs_config)
    exec_role_arn, task_role_arn = ensure_roles(
        session,
        config.project_name,
        config.aws_region,
        [secret for secret in configured_secret_arns if secret],
        report_step,
    )
    return _update_config_with_roles(config, exec_role_arn, task_role_arn)


def run_ecr_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Create ECR repositories for images.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Setting up ECR repositories...[/cyan]")
    console.print("[dim]This stores the sre-agent container image for ECS.[/dim]")
    session = create_session(ecs_config)

    report_step("Ensuring sre-agent repository")
    sre_agent_uri = ensure_repository(session, config.ecr_repo_sre_agent)
    return _update_config_with_ecr(config, sre_agent_uri)


def run_build_push_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Build and push container images.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Building and pushing images...[/cyan]")
    console.print("[dim]This builds the agent image and uses Slack MCP from GHCR.[/dim]")
    if not config.ecr_sre_agent_uri:
        console.print("[yellow]ECR repository is missing. Run the ECR step first.[/yellow]")
        return None

    session = create_session(ecs_config)
    image_config = ImageBuildConfig(
        sre_agent_uri=config.ecr_sre_agent_uri,
        image_tag=config.image_tag,
    )
    task_cpu_architecture = build_and_push_images(
        session,
        project_root(),
        image_config,
        report_step,
    )
    if config.task_cpu_architecture != task_cpu_architecture:
        config.task_cpu_architecture = task_cpu_architecture
        _save_config_and_report(
            config,
            f"Saved task CPU architecture ({task_cpu_architecture}) to {{path}}",
        )
    return config


def run_task_definition_step(
    config: CliConfig, _ecs_config: EcsDeploymentConfig
) -> CliConfig | None:
    """Register the ECS task definition.

    Args:
        config: CLI configuration values.
        _ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Registering ECS task definition...[/cyan]")
    console.print("[dim]This defines how the ECS task runs the agent and Slack MCP.[/dim]")

    existing_channel = config.slack_channel_id
    slack_channel_id = (existing_channel or "").strip()
    if not slack_channel_id:
        user_input = questionary.text("Slack channel ID:").ask()
        slack_channel_id = (user_input or "").strip()
        if not slack_channel_id:
            console.print("[yellow]Slack channel ID is required.[/yellow]")
            return None

    if existing_channel != slack_channel_id:
        config.slack_channel_id = slack_channel_id
        _save_config_and_report(config, "Saved Slack channel ID to {path}")

    updated_ecs_config = ecs_config_from_cli(config)
    session = create_session(updated_ecs_config)
    task_definition_arn = register_task_definition(session, updated_ecs_config, report_step)
    return _update_config_with_task_definition(config, task_definition_arn)


def run_cluster_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Ensure the ECS cluster exists.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Ensuring ECS cluster...[/cyan]")
    console.print("[dim]This creates the ECS cluster if it does not exist.[/dim]")
    session = create_session(ecs_config)
    cluster_arn = ensure_cluster(session, config.cluster_name)
    return _update_config_with_cluster(config, cluster_arn)


def run_task_step(config: CliConfig, _ecs_config: EcsDeploymentConfig) -> None:
    """Show next-step guidance after deployment.

    Args:
        config: CLI configuration values.
        _ecs_config: ECS deployment configuration.
    """
    if not config.task_definition_arn:
        console.print("[yellow]Task definition is missing. Register it first.[/yellow]")
        return
    if not config.private_subnet_ids or not config.security_group_id:
        console.print("[yellow]Network configuration is missing.[/yellow]")
        return

    console.print(
        "[dim]Deployment is ready. Use 'Run diagnosis job' to trigger a one-off run "
        "when needed.[/dim]"
    )


def start_one_off_task(
    config: CliConfig,
    ecs_config: EcsDeploymentConfig,
    container_overrides: list[dict[str, str | list[dict[str, str]]]] | None = None,
) -> tuple[Session, str]:
    """Start a one-off ECS task.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.
        container_overrides: Optional ECS container overrides.

    Returns:
        The active session and started task ARN.
    """
    if not config.task_definition_arn or not config.security_group_id:
        raise RuntimeError("Task definition and security group must be configured first.")

    console.print("[cyan]Running ECS task...[/cyan]")
    session = create_session(ecs_config)
    ensure_service_linked_role(session, report_step)
    task_arn = run_task(
        session,
        ecs_config,
        container_overrides,
    )
    console.print(f"[green]Task started: {task_arn}[/green]")
    return session, task_arn


def wait_for_task_completion(session: Session, cluster_name: str, task_arn: str) -> None:
    """Wait for task completion and report outcome.

    Args:
        session: Session wrapper used by AWS ECS helpers.
        cluster_name: ECS cluster name.
        task_arn: Running task ARN.
    """
    console.print("[cyan]Waiting for diagnosis task to complete...[/cyan]")
    completed, message = wait_for_ecs_task_completion(session, cluster_name, task_arn)
    if completed:
        console.print(f"[green]{message}[/green]")
        return
    console.print(f"[yellow]Diagnosis task failed: {message}[/yellow]")


def prompt_diagnosis_inputs() -> tuple[str, str, int] | None:
    """Prompt for one-off diagnosis input values.

    Returns:
        Cleaned service/log/time-range values, or None when cancelled/invalid.
    """
    service_name = (questionary.text("Service name:").ask() or "").strip()
    if not service_name:
        console.print("[yellow]Service name is required.[/yellow]")
        return None

    log_group = (questionary.text("CloudWatch log group:").ask() or "").strip()
    if not log_group:
        console.print("[yellow]CloudWatch log group is required.[/yellow]")
        return None

    raw_minutes = (questionary.text("Time range minutes:", default="10").ask() or "").strip()
    if not raw_minutes:
        console.print("[yellow]Time range minutes is required.[/yellow]")
        return None
    try:
        time_range_minutes = int(raw_minutes)
    except ValueError:
        console.print("[yellow]Time range minutes must be an integer.[/yellow]")
        return None
    if time_range_minutes <= 0:
        console.print("[yellow]Time range minutes must be greater than 0.[/yellow]")
        return None
    return service_name, log_group, time_range_minutes


def build_container_overrides(
    service_name: str,
    log_group: str,
    time_range_minutes: int,
) -> list[dict[str, str | list[dict[str, str]]]]:
    """Build container overrides for a diagnosis job run.

    Args:
        service_name: Target service name for diagnosis.
        log_group: CloudWatch log group name.
        time_range_minutes: Diagnosis window in minutes.

    Returns:
        ECS container overrides payload.
    """
    return [
        {
            "name": "sre-agent",
            "environment": [
                {"name": "SERVICE_NAME", "value": service_name},
                {"name": "LOG_GROUP", "value": log_group},
                {"name": "TIME_RANGE_MINUTES", "value": str(time_range_minutes)},
            ],
        }
    ]


def print_cleanup_summary(config: CliConfig) -> None:
    """Print a summary of resources to be cleaned up.

    Args:
        config: CLI configuration values.
    """
    console.print("[bold]Resources to clean up:[/bold]")
    console.print(f"- VPC: {config.vpc_id or 'not set'}")
    console.print(f"- Private subnets: {', '.join(config.private_subnet_ids) or 'not set'}")
    console.print(f"- Security group: {config.security_group_id or 'not set'}")
    console.print(f"- ECS cluster: {config.cluster_name}")
    console.print(f"- Task definition: {config.task_definition_arn or 'not set'}")
    console.print(f"- ECR repo: {config.ecr_repo_sre_agent}")
    console.print(f"- Legacy Slack ECR repo (if present): {config.ecr_repo_slack_mcp}")
    console.print(f"- Log group: {config.log_group_name}")
    console.print(f"- Secrets: {joined_secret_names(config)}")
    iam_execution_role, iam_task_role = default_iam_role_names(config)
    iam_roles = f"{iam_execution_role}, {iam_task_role}"
    console.print(f"- IAM roles: {iam_roles}")


def print_deployment_summary(config: CliConfig) -> None:
    """Print a summary of resources that will be created.

    Args:
        config: CLI configuration values.
    """
    console.print("[bold]Deployment plan:[/bold]")
    console.print("- Create a new VPC with one public and one private subnet")
    console.print("- Create an internet gateway, NAT gateway, and route tables")
    console.print("- Create a dedicated security group for ECS tasks")
    console.print(f"- Store secrets in Secrets Manager ({joined_secret_names(config)})")
    iam_execution_role, iam_task_role = default_iam_role_names(config)
    iam_roles = f"{iam_execution_role} and {iam_task_role}"
    console.print(f"- Create IAM roles: {iam_roles}")
    console.print(f"- Create ECR repository: {config.ecr_repo_sre_agent}")
    console.print("- Build and push the sre-agent container image")
    console.print("- Use Slack MCP image directly from GHCR")
    console.print(f"- Register ECS task definition: {config.task_family}")
    console.print(f"- Ensure ECS cluster: {config.cluster_name}")
    console.print("- Optionally run a one-off diagnosis job")


def reset_cleanup_state(config: CliConfig) -> None:
    """Clear deployment state after clean up.

    Args:
        config: CLI configuration values.
    """
    config.vpc_id = None
    config.private_subnet_ids = []
    config.security_group_id = None
    config.secret_anthropic_arn = None
    config.secret_slack_bot_arn = None
    config.secret_github_token_arn = None
    config.exec_role_arn = None
    config.task_role_arn = None
    config.ecr_sre_agent_uri = None
    config.task_definition_arn = None
    config.cluster_arn = None

    _save_config_and_report(config, "Cleared deployment state in {path}")


def report_step(message: str) -> None:
    """Report deployment progress to the user.

    Args:
        message: Progress message to display.
    """
    console.print(f"[bold cyan]•[/bold cyan] {message}")


def _ensure_secret(
    session: Session,
    name: str,
    label: str,
    existing_arn: str | None,
    configured_value: str | None,
) -> str | None:
    """Ensure a secret exists and return its ARN.

    Args:
        session: Boto3 session wrapper for AWS calls.
        name: Secret name to use.
        label: Human-readable label for prompts.
        existing_arn: Existing ARN if already stored.
        configured_value: Value from local configuration.

    Returns:
        The secret ARN, or None if creation failed.
    """
    info = get_secret_info(session, name)
    if info and info.scheduled_for_deletion:
        report_step(f"Secret {name} is scheduled for deletion. Restoring it")
        arn = restore_secret(session, name)
        report_step(f"Restored secret for {label}")
        return arn

    if info:
        if existing_arn and existing_arn == info.arn:
            report_step(f"Using saved secret ARN for {label}")
        elif existing_arn and existing_arn != info.arn:
            report_step(f"Saved secret ARN for {label} is stale. Using current secret")
        else:
            report_step(f"Found existing secret for {label}")
        return info.arn

    if existing_arn:
        report_step(f"Saved secret ARN for {label} was not found. Recreating secret")

    value = (configured_value or "").strip()
    if value:
        report_step(f"Creating secret {name} from configured {label}")
        return create_secret(session, name, value)

    value = questionary.password(f"Enter {label}:").ask()
    if not value:
        console.print("[yellow]Secret value is required.[/yellow]")
        return None

    report_step(f"Creating secret {name}")
    return create_secret(session, name, value)


def _update_config_with_secrets(
    config: CliConfig,
    anthropic_arn: str,
    slack_arn: str,
    github_arn: str,
) -> CliConfig:
    """Persist secret ARNs to config.

    Args:
        config: CLI configuration values.
        anthropic_arn: Anthropic secret ARN.
        slack_arn: Slack bot token secret ARN.
        github_arn: GitHub token secret ARN.

    Returns:
        The updated configuration.
    """
    config.secret_anthropic_arn = anthropic_arn
    config.secret_slack_bot_arn = slack_arn
    config.secret_github_token_arn = github_arn
    return _save_config_and_report(config, "Saved secrets configuration to {path}")


def _update_config_with_roles(
    config: CliConfig,
    exec_role_arn: str,
    task_role_arn: str,
) -> CliConfig:
    """Persist role ARNs to config.

    Args:
        config: CLI configuration values.
        exec_role_arn: Execution role ARN.
        task_role_arn: Task role ARN.

    Returns:
        The updated configuration.
    """
    config.exec_role_arn = exec_role_arn
    config.task_role_arn = task_role_arn
    return _save_config_and_report(config, "Saved IAM role configuration to {path}")


def _update_config_with_ecr(config: CliConfig, sre_agent_uri: str) -> CliConfig:
    """Persist ECR repository URI to config.

    Args:
        config: CLI configuration values.
        sre_agent_uri: SRE agent repository URI.

    Returns:
        The updated configuration.
    """
    config.ecr_sre_agent_uri = sre_agent_uri
    return _save_config_and_report(config, "Saved ECR repository configuration to {path}")


def _update_config_with_task_definition(config: CliConfig, task_definition_arn: str) -> CliConfig:
    """Persist task definition ARN to config.

    Args:
        config: CLI configuration values.
        task_definition_arn: Task definition ARN.

    Returns:
        The updated configuration.
    """
    config.task_definition_arn = task_definition_arn
    return _save_config_and_report(config, "Saved task definition to {path}")


def _update_config_with_cluster(config: CliConfig, cluster_arn: str) -> CliConfig:
    """Persist cluster ARN to config.

    Args:
        config: CLI configuration values.
        cluster_arn: Cluster ARN.

    Returns:
        The updated configuration.
    """
    config.cluster_arn = cluster_arn
    return _save_config_and_report(config, "Saved cluster configuration to {path}")


def _update_config_with_network(config: CliConfig, network: NetworkSelection) -> CliConfig:
    """Persist network selection to config.

    Args:
        config: CLI configuration values.
        network: Selected network configuration.

    Returns:
        The updated configuration.
    """
    config.vpc_id = network.vpc_id
    config.private_subnet_ids = network.private_subnet_ids
    return _save_config_and_report(config, "Saved network configuration to {path}")


def _update_config_with_security_group(config: CliConfig, group: SecurityGroupInfo) -> CliConfig:
    """Persist security group selection to config.

    Args:
        config: CLI configuration values.
        group: Security group result.

    Returns:
        The updated configuration.
    """
    config.security_group_id = group.group_id
    return _save_config_and_report(config, "Saved security group to {path}")


def _save_config_and_report(config: CliConfig, message_template: str) -> CliConfig:
    """Save CLI config and print a formatted success message.

    Args:
        config: CLI configuration values.
        message_template: Message template containing `{path}` placeholder.

    Returns:
        The saved configuration.
    """
    path = save_config(config)
    message = message_template.format(path=path)
    console.print(f"[green]{message}[/green]")
    return config
