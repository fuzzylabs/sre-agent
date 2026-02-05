"""Remote deployment mode for the CLI."""

from datetime import UTC, datetime
from typing import Any

import questionary

from sre_agent.cli.config import CliConfig, load_config, save_config
from sre_agent.cli.mode.paths import project_root
from sre_agent.cli.ui import console
from sre_agent.core.deployments.aws_ecs import (
    EcsDeploymentConfig,
    ImageBuildConfig,
    NetworkSelection,
    build_and_push_images,
    check_deployment,
    cleanup_resources,
    create_basic_vpc,
    create_secret,
    create_security_group,
    create_session,
    ensure_cluster,
    ensure_repository,
    ensure_roles,
    ensure_service_linked_role,
    get_secret_arn,
    register_task_definition,
    run_task,
)


def run_remote_mode() -> None:
    """Run the remote deployment actions."""
    target = questionary.select(
        "Remote Deployment:",
        choices=[
            "Deploy to AWS ECS",
            "Check deployment",
            "Clean up deployment",
            "Back",
        ],
    ).ask()

    if target in (None, "Back"):
        return

    if target == "Deploy to AWS ECS":
        _deploy_to_ecs()
    elif target == "Check deployment":
        _check_deployment()
    elif target == "Clean up deployment":
        _cleanup_menu()


def _deploy_to_ecs() -> None:
    """Run the full ECS deployment flow."""
    config = load_config()
    _print_deployment_summary(config)
    confirm = questionary.confirm(
        "Proceed with ECS deployment?",
        default=True,
    ).ask()
    if not confirm:
        console.print("[dim]Deployment cancelled.[/dim]")
        return

    steps = [
        _run_network_step,
        _run_security_group_step,
        _run_secrets_step,
        _run_iam_step,
        _run_ecr_step,
        _run_build_push_step,
        _run_task_definition_step,
        _run_cluster_step,
    ]
    updated = config
    for step in steps:
        ecs_config = _ecs_config_from_cli(updated)
        next_config = step(updated, ecs_config)
        if next_config is None:
            return
        updated = next_config

    ecs_config = _ecs_config_from_cli(updated)
    _run_task_step(updated, ecs_config)


def _check_deployment() -> None:
    """Check current deployment resources."""
    config = load_config()
    ecs_config = _ecs_config_from_cli(config)
    session = create_session(ecs_config)
    console.print("[cyan]Checking current deployment...[/cyan]")
    results = check_deployment(session, ecs_config)
    for name, status in results.items():
        console.print(f"- {name}: {status}")


def _cleanup_menu() -> None:
    """Clean up deployment resources."""
    console.print("[cyan]Clean up deployment resources[/cyan]")
    console.print("[dim]This removes ECS resources created by the deployment flow.[/dim]")

    config = load_config()
    ecs_config = _ecs_config_from_cli(config)
    _print_cleanup_summary(config)

    confirm = questionary.confirm(
        "This will delete the resources listed above. Continue?",
        default=False,
    ).ask()
    if not confirm:
        console.print("[dim]Clean up cancelled.[/dim]")
        return

    force_delete = questionary.confirm(
        "Delete secrets immediately (no recovery window)?",
        default=False,
    ).ask()

    cleanup_resources(ecs_config, _report_step, force_delete)
    _reset_cleanup_state(config)


def _ecs_config_from_cli(config: CliConfig) -> EcsDeploymentConfig:
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
        ecr_slack_mcp_uri=config.ecr_slack_mcp_uri,
        task_definition_arn=config.task_definition_arn,
        cluster_arn=config.cluster_arn,
        model=config.model,
        slack_channel_id=config.slack_channel_id,
        github_mcp_url=config.github_mcp_url,
        log_group_name=config.log_group_name,
        slack_mcp_host=config.slack_mcp_host,
        slack_mcp_port=config.slack_mcp_port,
    )


def _run_network_step(
    config: CliConfig,
    ecs_config: EcsDeploymentConfig,
) -> CliConfig | None:
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
    _report_step("Creating a new VPC with a private subnet and NAT gateway")
    network = create_basic_vpc(session, ecs_config.project_name, _report_step)
    return _update_config_with_network(config, network)


def _run_security_group_step(
    config: CliConfig,
    ecs_config: EcsDeploymentConfig,
) -> CliConfig | None:
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
    _report_step("Creating a new security group for ECS tasks")
    suffix = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    name = f"{ecs_config.project_name}-tasks-{suffix}"
    description = "Security group for SRE Agent ECS tasks"
    group = create_security_group(session, config.vpc_id, name, description)
    return _update_config_with_security_group(config, group)


def _run_secrets_step(
    config: CliConfig,
    ecs_config: EcsDeploymentConfig,
) -> CliConfig | None:
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

    anthropic_arn = _ensure_secret(
        session,
        config.secret_anthropic_name,
        "Anthropic API key",
        config.secret_anthropic_arn,
    )
    if anthropic_arn is None:
        return None

    slack_arn = _ensure_secret(
        session,
        config.secret_slack_bot_name,
        "Slack bot token",
        config.secret_slack_bot_arn,
    )
    if slack_arn is None:
        return None

    github_arn = _ensure_secret(
        session,
        config.secret_github_token_name,
        "GitHub token",
        config.secret_github_token_arn,
    )
    if github_arn is None:
        return None

    return _update_config_with_secrets(config, anthropic_arn, slack_arn, github_arn)


def _run_iam_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Create IAM roles for ECS tasks.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Setting up IAM roles...[/cyan]")
    console.print("[dim]This grants ECS tasks access to logs and secrets.[/dim]")

    secret_arns = [
        config.secret_anthropic_arn,
        config.secret_slack_bot_arn,
        config.secret_github_token_arn,
    ]
    if any(secret is None for secret in secret_arns):
        console.print("[yellow]Secrets are missing. Run the secrets step first.[/yellow]")
        return None

    session = create_session(ecs_config)
    exec_role_arn, task_role_arn = ensure_roles(
        session,
        config.project_name,
        config.aws_region,
        [secret for secret in secret_arns if secret],
        _report_step,
    )
    return _update_config_with_roles(config, exec_role_arn, task_role_arn)


def _run_ecr_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Create ECR repositories for images.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Setting up ECR repositories...[/cyan]")
    console.print("[dim]This stores the container images for ECS.[/dim]")
    session = create_session(ecs_config)

    _report_step("Ensuring sre-agent repository")
    sre_agent_uri = ensure_repository(session, config.ecr_repo_sre_agent)

    _report_step("Ensuring Slack MCP repository")
    slack_mcp_uri = ensure_repository(session, config.ecr_repo_slack_mcp)

    return _update_config_with_ecr(config, sre_agent_uri, slack_mcp_uri)


def _run_build_push_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
    """Build and push container images.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Building and pushing images...[/cyan]")
    console.print("[dim]This builds the agent image and mirrors the Slack MCP image.[/dim]")
    if not config.ecr_sre_agent_uri or not config.ecr_slack_mcp_uri:
        console.print("[yellow]ECR repositories are missing. Run the ECR step first.[/yellow]")
        return None

    session = create_session(ecs_config)
    root_dir = project_root()
    image_config = ImageBuildConfig(
        sre_agent_uri=config.ecr_sre_agent_uri,
        slack_mcp_uri=config.ecr_slack_mcp_uri,
        image_tag=config.image_tag,
    )
    build_and_push_images(
        session,
        root_dir,
        image_config,
        _report_step,
    )
    return config


def _run_task_definition_step(
    config: CliConfig,
    ecs_config: EcsDeploymentConfig,
) -> CliConfig | None:
    """Register the ECS task definition.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.

    Returns:
        The updated configuration, or None if cancelled.
    """
    console.print("[cyan]Registering ECS task definition...[/cyan]")
    console.print("[dim]This defines how the ECS task runs the agent and Slack MCP.[/dim]")
    if not config.slack_channel_id:
        slack_channel_id = questionary.text("Slack channel ID:").ask()
        if not slack_channel_id:
            console.print("[yellow]Slack channel ID is required.[/yellow]")
            return None
        config.slack_channel_id = slack_channel_id
        save_config(config)

    ecs_config = _ecs_config_from_cli(config)
    session = create_session(ecs_config)
    task_definition_arn = register_task_definition(session, ecs_config, _report_step)
    return _update_config_with_task_definition(config, task_definition_arn)


def _run_cluster_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
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


def _run_task_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> None:
    """Run a one-off ECS task.

    Args:
        config: CLI configuration values.
        ecs_config: ECS deployment configuration.
    """
    if not config.task_definition_arn:
        console.print("[yellow]Task definition is missing. Register it first.[/yellow]")
        return
    if not config.private_subnet_ids or not config.security_group_id:
        console.print("[yellow]Network configuration is missing.[/yellow]")
        return

    confirm = questionary.confirm("Run a one-off ECS task now?", default=False).ask()
    if not confirm:
        console.print("[dim]Skipping task run.[/dim]")
        return

    console.print("[cyan]Running ECS task...[/cyan]")
    session = create_session(ecs_config)
    ensure_service_linked_role(session, _report_step)
    task_arn = run_task(
        session,
        config.cluster_name,
        config.task_definition_arn,
        config.private_subnet_ids,
        config.security_group_id,
    )
    console.print(f"[green]Task started: {task_arn}[/green]")


def _ensure_secret(
    session: object,
    name: str,
    label: str,
    existing_arn: str | None,
) -> str | None:
    """Ensure a secret exists and return its ARN.

    Args:
        session: Boto3 session wrapper for AWS calls.
        name: Secret name to use.
        label: Human-readable label for prompts.
        existing_arn: Existing ARN if already stored.

    Returns:
        The secret ARN, or None if creation failed.
    """
    if existing_arn:
        _report_step(f"Using saved secret ARN for {label}")
        return existing_arn

    arn = get_secret_arn(session, name)
    if arn:
        _report_step(f"Found existing secret for {label}")
        return arn

    value = questionary.password(f"Enter {label}:").ask()
    if not value:
        console.print("[yellow]Secret value is required.[/yellow]")
        return None

    _report_step(f"Creating secret {name}")
    return create_secret(session, name, value)


def _print_cleanup_summary(config: CliConfig) -> None:
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
    console.print(f"- ECR repos: {config.ecr_repo_sre_agent}, {config.ecr_repo_slack_mcp}")
    console.print(f"- Log group: {config.log_group_name}")
    secret_names = ", ".join(
        [
            config.secret_anthropic_name,
            config.secret_slack_bot_name,
            config.secret_github_token_name,
        ]
    )
    console.print(f"- Secrets: {secret_names}")
    iam_roles = f"{config.project_name}-task-execution, {config.project_name}-task"
    console.print(f"- IAM roles: {iam_roles}")


def _print_deployment_summary(config: CliConfig) -> None:
    """Print a summary of resources that will be created.

    Args:
        config: CLI configuration values.
    """
    console.print("[bold]Deployment plan:[/bold]")
    console.print("- Create a new VPC with one public and one private subnet")
    console.print("- Create an internet gateway, NAT gateway, and route tables")
    console.print("- Create a dedicated security group for ECS tasks")
    secret_names = ", ".join(
        [
            config.secret_anthropic_name,
            config.secret_slack_bot_name,
            config.secret_github_token_name,
        ]
    )
    console.print(f"- Store secrets in Secrets Manager ({secret_names})")
    iam_roles = f"{config.project_name}-task-execution and {config.project_name}-task"
    console.print(f"- Create IAM roles: {iam_roles}")
    ecr_repos = f"{config.ecr_repo_sre_agent}, {config.ecr_repo_slack_mcp}"
    console.print(f"- Create ECR repositories: {ecr_repos}")
    console.print("- Build and push container images")
    console.print(f"- Register ECS task definition: {config.task_family}")
    console.print(f"- Ensure ECS cluster: {config.cluster_name}")
    console.print("- Optionally run a one-off ECS task")


def _reset_cleanup_state(config: CliConfig) -> None:
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
    config.ecr_slack_mcp_uri = None
    config.task_definition_arn = None
    config.cluster_arn = None

    path = save_config(config)
    console.print(f"[green]Cleared deployment state in {path}[/green]")


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
    path = save_config(config)
    console.print(f"[green]Saved secrets configuration to {path}[/green]")
    return config


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
    path = save_config(config)
    console.print(f"[green]Saved IAM role configuration to {path}[/green]")
    return config


def _update_config_with_ecr(
    config: CliConfig,
    sre_agent_uri: str,
    slack_mcp_uri: str,
) -> CliConfig:
    """Persist ECR repository URIs to config.

    Args:
        config: CLI configuration values.
        sre_agent_uri: SRE agent repository URI.
        slack_mcp_uri: Slack MCP repository URI.

    Returns:
        The updated configuration.
    """
    config.ecr_sre_agent_uri = sre_agent_uri
    config.ecr_slack_mcp_uri = slack_mcp_uri
    path = save_config(config)
    console.print(f"[green]Saved ECR repository configuration to {path}[/green]")
    return config


def _update_config_with_task_definition(config: CliConfig, task_definition_arn: str) -> CliConfig:
    """Persist task definition ARN to config.

    Args:
        config: CLI configuration values.
        task_definition_arn: Task definition ARN.

    Returns:
        The updated configuration.
    """
    config.task_definition_arn = task_definition_arn
    path = save_config(config)
    console.print(f"[green]Saved task definition to {path}[/green]")
    return config


def _update_config_with_cluster(config: CliConfig, cluster_arn: str) -> CliConfig:
    """Persist cluster ARN to config.

    Args:
        config: CLI configuration values.
        cluster_arn: Cluster ARN.

    Returns:
        The updated configuration.
    """
    config.cluster_arn = cluster_arn
    path = save_config(config)
    console.print(f"[green]Saved cluster configuration to {path}[/green]")
    return config


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
    path = save_config(config)
    console.print(f"[green]Saved network configuration to {path}[/green]")
    return config


def _update_config_with_security_group(config: CliConfig, group: Any) -> CliConfig:
    """Persist security group selection to config.

    Args:
        config: CLI configuration values.
        group: Security group result.

    Returns:
        The updated configuration.
    """
    config.security_group_id = group.group_id
    path = save_config(config)
    console.print(f"[green]Saved security group to {path}[/green]")
    return config


def _report_step(message: str) -> None:
    """Report deployment progress to the user.

    Args:
        message: Progress message to display.
    """
    console.print(f"[bold cyan]•[/bold cyan] {message}")
