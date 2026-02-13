"""AWS ECS remote deployment mode for the CLI."""

from collections.abc import Callable

import questionary

from sre_agent.cli.configuration.models import CliConfig
from sre_agent.cli.configuration.store import load_config, save_config
from sre_agent.cli.mode.remote.aws.ecs.errors import report_remote_error
from sre_agent.cli.mode.remote.aws.ecs.metadata import (
    STATUS_KEY_ECR_REPOSITORIES,
    STATUS_KEY_ECS_CLUSTER,
    STATUS_KEY_IAM_ROLES,
    STATUS_KEY_PRIVATE_SUBNETS,
    STATUS_KEY_SECRETS,
    STATUS_KEY_SECURITY_GROUP,
    STATUS_KEY_TASK_DEFINITION,
    STATUS_KEY_VPC,
)
from sre_agent.cli.mode.remote.aws.ecs.status import (
    collect_deployment_status,
    is_status_present,
    print_deployment_status_table,
    should_block_deploy,
)
from sre_agent.cli.mode.remote.aws.ecs.steps import (
    build_container_overrides,
    ecs_config_from_cli,
    print_cleanup_summary,
    print_deployment_summary,
    prompt_diagnosis_inputs,
    report_step,
    reset_cleanup_state,
    run_build_push_step,
    run_cluster_step,
    run_ecr_step,
    run_iam_step,
    run_network_step,
    run_secrets_step,
    run_security_group_step,
    run_task_definition_step,
    run_task_step,
    start_one_off_task,
    wait_for_task_completion,
)
from sre_agent.cli.presentation.console import console
from sre_agent.core.deployments.aws_ecs import (
    EcsDeploymentConfig,
    cleanup_resources,
    create_session,
    get_identity,
)

DeploymentStep = Callable[[CliConfig, EcsDeploymentConfig], CliConfig | None]


class _RepairCancelledError(Exception):
    """Signal that the repair flow was cancelled."""


def run_aws_ecs_mode() -> None:
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
            report_remote_error(exc)


def _aws_ecs_menu_choices(config: CliConfig) -> list[str]:
    """Return AWS ECS menu choices for the current deployment state.

    Args:
        config: CLI configuration values.

    Returns:
        Menu options appropriate for current deployment state.
    """
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


def _aws_ecs_menu_action(target: str) -> Callable[[], None] | None:
    """Return the action callable for a menu selection.

    Args:
        target: Menu option selected by the user.

    Returns:
        Matching action callable, if supported.
    """
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
        config.deployment.vpc_id
        and config.deployment.private_subnet_ids
        and config.deployment.security_group_id
        and config.deployment.task_definition_arn
        and config.deployment.cluster_arn
    )


def _deploy_to_ecs() -> None:
    """Run the full ECS deployment flow."""
    config = load_config()
    print_deployment_summary(config)
    confirm = questionary.confirm(
        "Proceed with ECS deployment?",
        default=True,
    ).ask()
    if not confirm:
        console.print("[dim]Deployment cancelled.[/dim]")
        return

    _validate_aws_session(ecs_config_from_cli(config))
    status = collect_deployment_status(config)
    if should_block_deploy(status):
        console.print(
            "[yellow]Deployment blocked because existing deployment resources "
            "were detected.[/yellow]"
        )
        print_deployment_status_table(config, status)
        console.print(
            "[dim]Use 'Repair deployment' to fix/reuse them, or 'Clean up deployment' first.[/dim]"
        )
        return

    steps: list[DeploymentStep] = [
        run_network_step,
        run_security_group_step,
        run_secrets_step,
        run_iam_step,
        run_ecr_step,
        run_build_push_step,
        run_task_definition_step,
        run_cluster_step,
    ]
    updated = config
    for step in steps:
        next_config = step(updated, ecs_config_from_cli(updated))
        if next_config is None:
            return
        updated = next_config

    run_task_step(updated, ecs_config_from_cli(updated))


def _check_deployment() -> None:
    """Check current deployment resources."""
    config = load_config()
    console.print("[cyan]Checking current deployment (live AWS status scan)...[/cyan]")
    results = collect_deployment_status(config)
    print_deployment_status_table(config, results)


def _run_diagnosis_job() -> None:
    """Run a temporary ECS task for one diagnosis job."""
    config = load_config()
    ecs_config = ecs_config_from_cli(config)

    if not config.deployment.task_definition_arn:
        console.print("[yellow]Task definition is missing. Deploy or repair first.[/yellow]")
        return
    if not config.deployment.private_subnet_ids or not config.deployment.security_group_id:
        console.print("[yellow]Network configuration is missing. Deploy or repair first.[/yellow]")
        return

    _validate_aws_session(ecs_config)
    confirm = questionary.confirm("Run one-off diagnosis job now?", default=True).ask()
    if not confirm:
        console.print("[dim]Diagnosis job cancelled.[/dim]")
        return

    inputs = prompt_diagnosis_inputs()
    if inputs is None:
        console.print("[dim]Diagnosis job cancelled.[/dim]")
        return

    session, task_arn = start_one_off_task(
        config,
        ecs_config,
        build_container_overrides(*inputs),
    )
    wait_for_task_completion(session, config.ecs.cluster_name, task_arn)


def _repair_deployment() -> None:
    """Repair missing or unhealthy deployment resources."""
    config = load_config()
    console.print("[cyan]Repairing deployment using strict live status checks...[/cyan]")

    current_status = collect_deployment_status(config)
    print_deployment_status_table(config, current_status)

    if all(is_status_present(status) for status in current_status.values()):
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
    """Run the ordered repair steps and return updated config.

    Args:
        config: CLI configuration values.

    Returns:
        Updated config after repair workflow.
    """
    updated = config
    task_definition_refresh_required = False

    updated, _ = _repair_network_if_needed(updated)

    for status_key, label, step, refresh_task_definition in _repair_steps():
        updated, repaired = _repair_resource_if_missing(updated, status_key, label, step)
        if repaired and refresh_task_definition:
            task_definition_refresh_required = True

    if _should_rebuild_images_during_repair():
        updated = _require_repair_step_result(
            run_build_push_step(updated, ecs_config_from_cli(updated))
        )

    updated, _ = _repair_task_definition_if_needed(
        updated,
        task_definition_refresh_required,
    )
    updated, _ = _repair_resource_if_missing(
        updated,
        STATUS_KEY_ECS_CLUSTER,
        "ECS cluster",
        run_cluster_step,
    )
    return updated


def _repair_steps() -> list[tuple[str, str, DeploymentStep, bool]]:
    """Return ordered resource repair steps.

    Returns:
        Ordered repair step metadata.
    """
    return [
        (STATUS_KEY_SECURITY_GROUP, "security group", run_security_group_step, False),
        (STATUS_KEY_SECRETS, "secrets", run_secrets_step, True),
        (STATUS_KEY_IAM_ROLES, "IAM roles", run_iam_step, True),
        (STATUS_KEY_ECR_REPOSITORIES, "ECR repositories", run_ecr_step, True),
    ]


def _repair_network_if_needed(config: CliConfig) -> tuple[CliConfig, bool]:
    """Repair VPC/subnets when missing.

    Args:
        config: CLI configuration values.

    Returns:
        Updated config and whether repair was performed.
    """
    status = collect_deployment_status(config)
    vpc_ok = is_status_present(status.get(STATUS_KEY_VPC, ""))
    subnets_ok = is_status_present(status.get(STATUS_KEY_PRIVATE_SUBNETS, ""))
    if vpc_ok and subnets_ok:
        return config, False

    console.print("[cyan]Repairing network resources...[/cyan]")
    updated = _require_repair_step_result(run_network_step(config, ecs_config_from_cli(config)))
    if updated.deployment.security_group_id:
        updated.deployment.security_group_id = None
        save_config(updated)
        report_step("Cleared saved security group. A new one will be created for the new VPC")
    return updated, True


def _repair_resource_if_missing(
    config: CliConfig,
    status_key: str,
    label: str,
    step: DeploymentStep,
) -> tuple[CliConfig, bool]:
    """Run a repair step when its status is not present.

    Args:
        config: CLI configuration values.
        status_key: Resource key in deployment status map.
        label: Display label for progress messages.
        step: Repair step callable.

    Returns:
        Updated config and whether repair was performed.
    """
    status = collect_deployment_status(config)
    if is_status_present(status.get(status_key, "")):
        return config, False

    console.print(f"[cyan]Repairing {label}...[/cyan]")
    updated = _require_repair_step_result(step(config, ecs_config_from_cli(config)))
    return updated, True


def _repair_task_definition_if_needed(
    config: CliConfig,
    refresh_required: bool,
) -> tuple[CliConfig, bool]:
    """Repair task definition when missing or after dependency changes.

    Args:
        config: CLI configuration values.
        refresh_required: Whether dependencies changed and force refresh is needed.

    Returns:
        Updated config and whether repair was performed.
    """
    status = collect_deployment_status(config)
    if not refresh_required and is_status_present(status.get(STATUS_KEY_TASK_DEFINITION, "")):
        return config, False

    console.print("[cyan]Repairing task definition...[/cyan]")
    updated = _require_repair_step_result(
        run_task_definition_step(config, ecs_config_from_cli(config))
    )
    return updated, True


def _should_rebuild_images_during_repair() -> bool:
    """Return true when the user wants image rebuild in repair.

    Returns:
        True when image rebuild should be included.
    """
    confirm = questionary.confirm(
        "Build and push images as part of repair?",
        default=False,
    ).ask()
    return bool(confirm)


def _require_repair_step_result(config: CliConfig | None) -> CliConfig:
    """Return config from a repair step or raise cancellation.

    Args:
        config: Optional config returned from a repair step.

    Returns:
        Required config value.

    Raises:
        _RepairCancelledError: If the step returned None.
    """
    if config is None:
        raise _RepairCancelledError()
    return config


def _report_repair_result(config: CliConfig) -> None:
    """Print final repair status and optional diagnosis run action.

    Args:
        config: Updated CLI configuration values.
    """
    final_status = collect_deployment_status(config)
    console.print("[cyan]Deployment status after repair:[/cyan]")
    print_deployment_status_table(config, final_status)

    if all(is_status_present(item) for item in final_status.values()):
        console.print("[green]Repair complete.[/green]")
        run_task_step(config, ecs_config_from_cli(config))
        return
    console.print(
        "[yellow]Repair finished with unresolved items. Review the status table.[/yellow]"
    )


def _cleanup_menu() -> None:
    """Clean up deployment resources."""
    console.print("[cyan]Clean up deployment resources[/cyan]")
    console.print("[dim]This removes ECS resources created by the deployment flow.[/dim]")

    config = load_config()
    ecs_config = ecs_config_from_cli(config)
    print_cleanup_summary(config)

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

    cleanup_resources(ecs_config, report_step, force_delete)
    reset_cleanup_state(config)


def _validate_aws_session(config: EcsDeploymentConfig) -> None:
    """Validate AWS session before running deployment actions.

    Args:
        config: ECS deployment configuration.
    """
    session = create_session(config)
    identity = get_identity(session)
    account = identity.get("Account", "unknown")
    arn = identity.get("Arn", "unknown")
    console.print(f"[dim]AWS identity: {arn} (account {account})[/dim]")
