"""Remote deployment mode for the CLI."""

from datetime import UTC, datetime
from typing import Any

import questionary
from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
    ProfileNotFound,
)
from rich.table import Table

from sre_agent.cli.config import CliConfig, load_config, save_config
from sre_agent.cli.env import load_env_values
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
    get_identity,
    get_secret_info,
    register_task_definition,
    restore_secret,
    run_task,
    wait_for_task_completion,
)


class _RepairCancelledError(Exception):
    """Signal that the repair flow was cancelled."""


def run_remote_mode() -> None:
    """Run the remote deployment actions."""
    target = questionary.select(
        "Remote Deployment:",
        choices=[
            "AWS ECS",
            "Back",
        ],
    ).ask()

    if target in (None, "Back"):
        return

    if target == "AWS ECS":
        _run_aws_ecs_menu()


def _run_aws_ecs_menu() -> None:
    """Run AWS ECS deployment actions."""
    while True:
        target = questionary.select(
            "AWS ECS:",
            choices=_aws_ecs_menu_choices(load_config()),
        ).ask()

        if target in (None, "Back"):
            return

        action = _aws_ecs_menu_action(target)
        if action is None:
            continue

        try:
            action()
        except Exception as exc:  # noqa: BLE001
            _report_remote_error(exc)


def _aws_ecs_menu_choices(config: CliConfig) -> list[str]:
    """Return AWS ECS menu choices for the current deployment state."""
    choices = [
        "Deploy to AWS ECS",
        "Check deployment status",
    ]
    if _has_completed_deployment(config):
        choices.extend(
            [
                "Run diagnosis job",
                "Repair deployment",
                "Clean up deployment",
            ]
        )
    choices.append("Back")
    return choices


def _aws_ecs_menu_action(target: str) -> Any:
    """Return the action callable for a menu selection."""
    return {
        "Deploy to AWS ECS": _deploy_to_ecs,
        "Check deployment status": _check_deployment,
        "Run diagnosis job": _run_diagnosis_job,
        "Repair deployment": _repair_deployment,
        "Clean up deployment": _cleanup_menu,
    }.get(target)


def _has_completed_deployment(config: CliConfig) -> bool:
    """Return true when config indicates an existing completed deployment.

    Args:
        config: CLI configuration values.

    Returns:
        True when core deployment state exists in config.
    """
    return bool(
        config.vpc_id
        and config.private_subnet_ids
        and config.security_group_id
        and config.task_definition_arn
        and config.cluster_arn
    )


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

    _validate_aws_session(_ecs_config_from_cli(config))
    status = _collect_deployment_status(config)
    if _should_block_deploy(status):
        console.print(
            "[yellow]Deployment blocked because existing deployment resources "
            "were detected.[/yellow]"
        )
        _print_deployment_status_table(config, status)
        console.print(
            "[dim]Use 'Repair deployment' to fix/reuse them, or 'Clean up deployment' first.[/dim]"
        )
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
    console.print("[cyan]Checking current deployment (live AWS status scan)...[/cyan]")
    results = _collect_deployment_status(config)
    _print_deployment_status_table(config, results)


def _run_diagnosis_job() -> None:
    """Run a temporary ECS task for one diagnosis job."""
    config = load_config()
    ecs_config = _ecs_config_from_cli(config)

    if not config.task_definition_arn:
        console.print("[yellow]Task definition is missing. Deploy or repair first.[/yellow]")
        return
    if not config.private_subnet_ids or not config.security_group_id:
        console.print("[yellow]Network configuration is missing. Deploy or repair first.[/yellow]")
        return

    _validate_aws_session(ecs_config)
    confirm = questionary.confirm("Run one-off diagnosis job now?", default=True).ask()
    if not confirm:
        console.print("[dim]Diagnosis job cancelled.[/dim]")
        return

    inputs = _prompt_diagnosis_inputs()
    if inputs is None:
        console.print("[dim]Diagnosis job cancelled.[/dim]")
        return

    session, task_arn = _start_one_off_task(
        config,
        ecs_config,
        _build_container_overrides(*inputs),
    )
    _wait_for_task_completion(session, config.cluster_name, task_arn)


def _repair_deployment() -> None:
    """Repair missing or unhealthy deployment resources."""
    config = load_config()
    console.print("[cyan]Repairing deployment using strict live status checks...[/cyan]")

    current_status = _collect_deployment_status(config)
    _print_deployment_status_table(config, current_status)

    if all(_is_status_present(status) for status in current_status.values()):
        console.print("[green]No repair actions required. All resources are healthy.[/green]")
        return

    confirm = questionary.confirm(
        "Attempt automatic repair for missing/unhealthy resources?",
        default=True,
    ).ask()
    if not confirm:
        console.print("[dim]Repair cancelled.[/dim]")
        return

    try:
        updated = _run_repair_flow(config)
    except _RepairCancelledError:
        console.print("[dim]Repair cancelled.[/dim]")
        return

    _report_repair_result(updated)


def _run_repair_flow(config: CliConfig) -> CliConfig:
    """Run the ordered repair steps and return updated config."""
    updated = config
    task_definition_refresh_required = False

    updated, _ = _repair_network_if_needed(updated)

    for status_key, label, step, refresh_task_definition in _repair_steps():
        updated, repaired = _repair_resource_if_missing(updated, status_key, label, step)
        if repaired and refresh_task_definition:
            task_definition_refresh_required = True

    if _should_rebuild_images_during_repair():
        updated = _require_repair_step_result(
            _run_build_push_step(updated, _ecs_config_from_cli(updated))
        )

    updated, _ = _repair_task_definition_if_needed(
        updated,
        task_definition_refresh_required,
    )
    updated, _ = _repair_resource_if_missing(
        updated,
        "ECS cluster",
        "ECS cluster",
        _run_cluster_step,
    )
    return updated


def _repair_steps() -> list[tuple[str, str, Any, bool]]:
    """Return ordered resource repair steps."""
    return [
        ("Security group", "security group", _run_security_group_step, False),
        ("Secrets", "secrets", _run_secrets_step, True),
        ("IAM roles", "IAM roles", _run_iam_step, True),
        ("ECR repositories", "ECR repositories", _run_ecr_step, True),
    ]


def _repair_network_if_needed(config: CliConfig) -> tuple[CliConfig, bool]:
    """Repair VPC/subnets when missing."""
    status = _collect_deployment_status(config)
    vpc_ok = _is_status_present(status.get("VPC", ""))
    subnets_ok = _is_status_present(status.get("Private subnets", ""))
    if vpc_ok and subnets_ok:
        return config, False

    console.print("[cyan]Repairing network resources...[/cyan]")
    updated = _require_repair_step_result(_run_network_step(config, _ecs_config_from_cli(config)))
    if updated.security_group_id:
        updated.security_group_id = None
        save_config(updated)
        _report_step("Cleared saved security group. A new one will be created for the new VPC")
    return updated, True


def _repair_resource_if_missing(
    config: CliConfig,
    status_key: str,
    label: str,
    step: Any,
) -> tuple[CliConfig, bool]:
    """Run a repair step when its status is not present."""
    status = _collect_deployment_status(config)
    if _is_status_present(status.get(status_key, "")):
        return config, False

    console.print(f"[cyan]Repairing {label}...[/cyan]")
    updated = _require_repair_step_result(step(config, _ecs_config_from_cli(config)))
    return updated, True


def _repair_task_definition_if_needed(
    config: CliConfig,
    refresh_required: bool,
) -> tuple[CliConfig, bool]:
    """Repair task definition when missing or after dependency changes."""
    status = _collect_deployment_status(config)
    if not refresh_required and _is_status_present(status.get("Task definition", "")):
        return config, False

    console.print("[cyan]Repairing task definition...[/cyan]")
    updated = _require_repair_step_result(
        _run_task_definition_step(config, _ecs_config_from_cli(config))
    )
    return updated, True


def _should_rebuild_images_during_repair() -> bool:
    """Return true when the user wants image rebuild in repair."""
    confirm = questionary.confirm(
        "Build and push images as part of repair?",
        default=False,
    ).ask()
    return bool(confirm)


def _require_repair_step_result(config: CliConfig | None) -> CliConfig:
    """Return config from a repair step or raise cancellation."""
    if config is None:
        raise _RepairCancelledError()
    return config


def _report_repair_result(config: CliConfig) -> None:
    """Print final repair status and optional diagnosis run action."""
    final_status = _collect_deployment_status(config)
    console.print("[cyan]Deployment status after repair:[/cyan]")
    _print_deployment_status_table(config, final_status)

    if all(_is_status_present(item) for item in final_status.values()):
        console.print("[green]Repair complete.[/green]")
        _run_task_step(config, _ecs_config_from_cli(config))
        return
    console.print(
        "[yellow]Repair finished with unresolved items. Review the status table.[/yellow]"
    )


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
    console.print("[dim]This stores the sre-agent container image for ECS.[/dim]")
    session = create_session(ecs_config)

    _report_step("Ensuring sre-agent repository")
    sre_agent_uri = ensure_repository(session, config.ecr_repo_sre_agent)

    return _update_config_with_ecr(config, sre_agent_uri)


def _run_build_push_step(config: CliConfig, ecs_config: EcsDeploymentConfig) -> CliConfig | None:
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
    root_dir = project_root()
    image_config = ImageBuildConfig(
        sre_agent_uri=config.ecr_sre_agent_uri,
        image_tag=config.image_tag,
    )
    task_cpu_architecture = build_and_push_images(
        session,
        root_dir,
        image_config,
        _report_step,
    )
    if config.task_cpu_architecture != task_cpu_architecture:
        config.task_cpu_architecture = task_cpu_architecture
        path = save_config(config)
        console.print(
            f"[green]Saved task CPU architecture ({task_cpu_architecture}) to {path}[/green]"
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
    """Show next-step guidance after deployment.

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

    console.print(
        "[dim]Deployment is ready. Use 'Run diagnosis job' to trigger a one-off run "
        "when needed.[/dim]"
    )


def _start_one_off_task(
    config: CliConfig,
    ecs_config: EcsDeploymentConfig,
    container_overrides: list[dict[str, Any]] | None = None,
) -> tuple[Any, str]:
    """Start a one-off ECS task."""
    if not config.task_definition_arn or not config.security_group_id:
        raise RuntimeError("Task definition and security group must be configured first.")

    console.print("[cyan]Running ECS task...[/cyan]")
    session = create_session(ecs_config)
    ensure_service_linked_role(session, _report_step)
    task_arn = run_task(
        session,
        ecs_config,
        container_overrides,
    )
    console.print(f"[green]Task started: {task_arn}[/green]")
    return session, task_arn


def _wait_for_task_completion(session: Any, cluster_name: str, task_arn: str) -> None:
    """Wait for task completion and report outcome."""
    console.print("[cyan]Waiting for diagnosis task to complete...[/cyan]")
    completed, message = wait_for_task_completion(session, cluster_name, task_arn)
    if completed:
        console.print(f"[green]{message}[/green]")
        return
    console.print(f"[yellow]Diagnosis task failed: {message}[/yellow]")


def _prompt_diagnosis_inputs() -> tuple[str, str, int] | None:
    """Prompt for one-off diagnosis input values."""
    service_name = questionary.text("Service name:").ask()
    if not service_name:
        console.print("[yellow]Service name is required.[/yellow]")
        return None

    log_group = questionary.text("CloudWatch log group:").ask()
    if not log_group:
        console.print("[yellow]CloudWatch log group is required.[/yellow]")
        return None

    raw_minutes = questionary.text("Time range minutes:", default="10").ask()
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
    return service_name.strip(), log_group.strip(), time_range_minutes


def _build_container_overrides(
    service_name: str,
    log_group: str,
    time_range_minutes: int,
) -> list[dict[str, Any]]:
    """Build container overrides for a diagnosis job run."""
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


def _ensure_secret(
    session: Any,
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
        _report_step(f"Secret {name} is scheduled for deletion. Restoring it")
        arn = restore_secret(session, name)
        _report_step(f"Restored secret for {label}")
        return arn

    if info:
        if existing_arn and existing_arn == info.arn:
            _report_step(f"Using saved secret ARN for {label}")
        elif existing_arn and existing_arn != info.arn:
            _report_step(f"Saved secret ARN for {label} is stale. Using current secret")
        else:
            _report_step(f"Found existing secret for {label}")
        return info.arn

    if existing_arn:
        _report_step(f"Saved secret ARN for {label} was not found. Recreating secret")

    value = (configured_value or "").strip()
    if value:
        _report_step(f"Creating secret {name} from configured {label}")
        return create_secret(session, name, value)

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
    console.print(f"- ECR repo: {config.ecr_repo_sre_agent}")
    console.print(f"- Legacy Slack ECR repo (if present): {config.ecr_repo_slack_mcp}")
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
    console.print(f"- Create ECR repository: {config.ecr_repo_sre_agent}")
    console.print("- Build and push the sre-agent container image")
    console.print("- Use Slack MCP image directly from GHCR")
    console.print(f"- Register ECS task definition: {config.task_family}")
    console.print(f"- Ensure ECS cluster: {config.cluster_name}")
    console.print("- Optionally run a one-off diagnosis job")


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
) -> CliConfig:
    """Persist ECR repository URIs to config.

    Args:
        config: CLI configuration values.
        sre_agent_uri: SRE agent repository URI.

    Returns:
        The updated configuration.
    """
    config.ecr_sre_agent_uri = sre_agent_uri
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


def _validate_aws_session(config: EcsDeploymentConfig) -> None:
    """Validate AWS session before running deployment actions."""
    session = create_session(config)
    identity = get_identity(session)
    account = identity.get("Account", "unknown")
    arn = identity.get("Arn", "unknown")
    console.print(f"[dim]AWS identity: {arn} (account {account})[/dim]")


def _report_remote_error(exc: Exception) -> None:
    """Render remote deployment errors with actionable guidance."""
    if _is_aws_auth_error(exc):
        console.print(
            "[red]AWS authentication failed. Your credentials are missing, invalid, "
            "or expired.[/red]"
        )
        console.print(
            "[dim]If using AWS profile/SSO, run: aws sso login --profile <profile>. "
            "If using temporary keys, refresh AWS_SESSION_TOKEN and retry.[/dim]"
        )
        return

    if _is_aws_endpoint_error(exc):
        console.print("[red]Could not reach AWS endpoint from this environment.[/red]")
        console.print("[dim]Check network connectivity and AWS region configuration.[/dim]")
        return

    console.print(f"[red]Remote deployment failed: {exc}[/red]")


def _is_aws_auth_error(exc: Exception) -> bool:
    """Return true when an exception chain indicates AWS auth issues."""
    auth_codes = {
        "ExpiredToken",
        "ExpiredTokenException",
        # spellchecker:ignore-next-line
        "UnrecognizedClientException",
        "InvalidClientTokenId",
        "InvalidSignatureException",
        "AccessDenied",
        "AccessDeniedException",
    }
    for item in _exception_chain(exc):
        if isinstance(item, (NoCredentialsError, ProfileNotFound)):
            return True
        if isinstance(item, ClientError):
            code = str(item.response.get("Error", {}).get("Code", ""))
            if code in auth_codes:
                return True
        text = str(item)
        if "security token included in the request is expired" in text.lower():
            return True
    return False


def _is_aws_endpoint_error(exc: Exception) -> bool:
    """Return true when an exception chain indicates AWS endpoint/network errors."""
    return any(isinstance(item, EndpointConnectionError) for item in _exception_chain(exc))


def _exception_chain(exc: BaseException) -> list[BaseException]:
    """Return exceptions in cause/context chain."""
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        chain.append(current)
        seen.add(id(current))
        next_item = current.__cause__ or current.__context__
        current = next_item
    return chain


def _collect_deployment_status(config: CliConfig) -> dict[str, str]:
    """Collect live deployment status from AWS."""
    ecs_config = _ecs_config_from_cli(config)
    session = create_session(ecs_config)
    return check_deployment(session, ecs_config)


def _print_deployment_status_table(config: CliConfig, results: dict[str, str]) -> None:
    """Print a deployment status table."""
    targets = _deployment_resource_targets(config)

    table = Table(title="Deployment resources", show_header=True, header_style="bold cyan")
    table.add_column("Resource", style="white", no_wrap=True)
    table.add_column("Name/ID", style="bright_white")
    table.add_column("Status", style="white", no_wrap=True)

    for name, status in results.items():
        table.add_row(name, targets.get(name, "-"), _style_status(status))

    console.print(table)


def _is_status_present(status: str) -> bool:
    """Return true when a resource status is healthy/present."""
    return status.startswith("present")


def _should_block_deploy(results: dict[str, str]) -> bool:
    """Return true when deploy should be blocked to avoid duplicate resources."""
    return any(
        _status_indicates_existing_resource(resource, status)
        for resource, status in results.items()
    )


def _status_indicates_existing_resource(resource: str, status: str) -> bool:
    """Return true when a status means resources already exist or are uncertain."""
    if status == "not set":
        return False
    if status.startswith("missing"):
        return False
    if resource == "ECS cluster" and status.strip().lower() == "status inactive":
        return False
    return (
        status.startswith("present") or status.startswith("status ") or status.startswith("error")
    )


def _deployment_resource_targets(config: CliConfig) -> dict[str, str]:
    """Return display names/IDs for deployment resources."""
    task_definition_name = config.task_family
    if config.task_definition_arn:
        task_definition_name = f"{config.task_family} ({config.task_definition_arn})"

    iam_targets = [
        config.exec_role_arn or f"{config.project_name}-task-execution",
        config.task_role_arn or f"{config.project_name}-task",
    ]
    ecr_targets = [config.ecr_sre_agent_uri or config.ecr_repo_sre_agent]
    cluster_target = config.cluster_name
    if config.cluster_arn:
        cluster_target = f"{config.cluster_name} ({config.cluster_arn})"

    return {
        "VPC": config.vpc_id or "not set",
        "Private subnets": ", ".join(config.private_subnet_ids) or "not set",
        "Security group": config.security_group_id or "not set",
        "Secrets": ", ".join(
            [
                config.secret_anthropic_name,
                config.secret_slack_bot_name,
                config.secret_github_token_name,
            ]
        ),
        "IAM roles": ", ".join(iam_targets),
        "ECR repositories": ", ".join(ecr_targets),
        "Log group": config.log_group_name,
        "Task definition": task_definition_name,
        "ECS cluster": cluster_target,
    }


def _style_status(status: str) -> str:
    """Return colourised status text for terminal output."""
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
