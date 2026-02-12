"""ECS task and cluster helpers."""

import time
from collections.abc import Callable
from typing import Any, cast

from botocore.exceptions import ClientError

from sre_agent.core.deployments.aws_ecs.models import EcsDeploymentConfig

SRE_AGENT_CONTAINER_NAME = "sre-agent"
SLACK_MCP_IMAGE = "ghcr.io/korotovsky/slack-mcp-server:latest"


def ensure_log_group(session: Any, log_group_name: str) -> None:
    """Ensure a CloudWatch log group exists."""
    logs = session.client("logs")
    try:
        logs.create_log_group(logGroupName=log_group_name)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code != "ResourceAlreadyExistsException":
            raise RuntimeError(f"Failed to create log group: {exc}") from exc


def register_task_definition(
    session: Any,
    config: EcsDeploymentConfig,
    reporter: Callable[[str], None],
) -> str:
    """Register the ECS task definition."""
    cpu_architecture = _normalise_cpu_architecture(config.task_cpu_architecture)
    if not config.exec_role_arn or not config.task_role_arn:
        raise RuntimeError("Task roles must be created before registering the task definition.")
    if not config.ecr_sre_agent_uri:
        raise RuntimeError("ECR repository for sre-agent must be created first.")
    if (
        not config.secret_anthropic_arn
        or not config.secret_github_token_arn
        or not config.secret_slack_bot_arn
    ):
        raise RuntimeError("Secrets must be created before registering the task definition.")
    if not config.slack_channel_id:
        raise RuntimeError("Slack channel ID is required for the task definition.")

    reporter("Ensuring CloudWatch log group for task logs")
    ensure_log_group(session, config.log_group_name)

    ecs = session.client("ecs")
    slack_mcp_url = f"http://localhost:{config.slack_mcp_port}/sse"

    container_definitions = [
        {
            "name": SRE_AGENT_CONTAINER_NAME,
            "image": f"{config.ecr_sre_agent_uri}:{config.image_tag}",
            "essential": True,
            "environment": [
                {"name": "AWS_REGION", "value": config.aws_region},
                {"name": "MODEL", "value": config.model},
                {"name": "SLACK_CHANNEL_ID", "value": config.slack_channel_id},
                {"name": "SLACK_MCP_URL", "value": slack_mcp_url},
                {"name": "GITHUB_MCP_URL", "value": config.github_mcp_url},
            ],
            "secrets": [
                {
                    "name": "ANTHROPIC_API_KEY",
                    "valueFrom": config.secret_anthropic_arn,
                },
                {
                    "name": "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "valueFrom": config.secret_github_token_arn,
                },
            ],
            "dependsOn": [{"containerName": "slack", "condition": "START"}],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": config.log_group_name,
                    "awslogs-region": config.aws_region,
                    "awslogs-stream-prefix": "sre-agent",
                },
            },
        },
        {
            "name": "slack",
            "image": SLACK_MCP_IMAGE,
            "essential": True,
            "environment": [
                {"name": "SLACK_MCP_ADD_MESSAGE_TOOL", "value": config.slack_channel_id},
                {"name": "SLACK_MCP_HOST", "value": config.slack_mcp_host},
                {"name": "SLACK_MCP_PORT", "value": str(config.slack_mcp_port)},
            ],
            "secrets": [
                {"name": "SLACK_MCP_XOXB_TOKEN", "valueFrom": config.secret_slack_bot_arn},
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": config.log_group_name,
                    "awslogs-region": config.aws_region,
                    "awslogs-stream-prefix": "slack",
                },
            },
        },
    ]

    response = ecs.register_task_definition(
        family=config.task_family,
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        runtimePlatform={
            "cpuArchitecture": cpu_architecture,
            "operatingSystemFamily": "LINUX",
        },
        cpu=str(config.task_cpu),
        memory=str(config.task_memory),
        executionRoleArn=config.exec_role_arn,
        taskRoleArn=config.task_role_arn,
        containerDefinitions=container_definitions,
    )
    return cast(str, response["taskDefinition"]["taskDefinitionArn"])


def _normalise_cpu_architecture(value: str) -> str:
    """Return a validated ECS CPU architecture."""
    architecture = value.strip().upper()
    if architecture in {"X86_64", "ARM64"}:
        return architecture
    raise RuntimeError(f"Unsupported ECS CPU architecture '{value}'. Use X86_64 or ARM64.")


def ensure_cluster(session: Any, cluster_name: str) -> str:
    """Ensure an ECS cluster exists."""
    ecs = session.client("ecs")
    response = ecs.describe_clusters(clusters=[cluster_name])
    clusters = response.get("clusters", [])
    if clusters:
        cluster = clusters[0]
        status = str(cluster.get("status", ""))
        cluster_arn = cast(str, cluster["clusterArn"])
        if status == "ACTIVE":
            return cluster_arn
        if status != "INACTIVE":
            raise RuntimeError(
                f"ECS cluster {cluster_name} is in unexpected status {status} and cannot be used."
            )

    # If the cluster does not exist or is inactive, create it.
    response = ecs.create_cluster(clusterName=cluster_name)
    return cast(str, response["cluster"]["clusterArn"])


def run_task(
    session: Any,
    config: EcsDeploymentConfig,
    container_overrides: list[dict[str, Any]] | None = None,
) -> str:
    """Run a one-off ECS task."""
    if not config.task_definition_arn:
        raise RuntimeError("Task definition is missing. Register it before running tasks.")
    if not config.security_group_id or not config.private_subnet_ids:
        raise RuntimeError(
            "Network configuration is missing. Configure subnets and security group."
        )

    ecs = session.client("ecs")
    request: dict[str, Any] = {
        "cluster": config.cluster_name,
        "launchType": "FARGATE",
        "taskDefinition": config.task_definition_arn,
        "count": 1,
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "subnets": config.private_subnet_ids,
                "securityGroups": [config.security_group_id],
                "assignPublicIp": "DISABLED",
            }
        },
    }
    if container_overrides:
        request["overrides"] = {"containerOverrides": container_overrides}

    try:
        response = ecs.run_task(**request)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "ClusterNotFoundException":
            raise RuntimeError(
                f"ECS cluster '{config.cluster_name}' is missing or inactive. "
                "Re-run deployment to recreate it."
            ) from exc
        raise RuntimeError(f"Failed to run ECS task: {exc}") from exc

    tasks = response.get("tasks", [])
    if not tasks:
        failures = response.get("failures", [])
        raise RuntimeError(f"Failed to run task: {failures}")
    return cast(str, tasks[0]["taskArn"])


def wait_for_task_completion(
    session: Any,
    cluster_name: str,
    task_arn: str,
    timeout_seconds: int = 1800,
    poll_interval_seconds: int = 5,
) -> tuple[bool, str]:
    """Wait for a task to stop and report container exit status."""
    ecs = session.client("ecs")
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        response = ecs.describe_tasks(cluster=cluster_name, tasks=[task_arn])
        tasks = response.get("tasks", [])
        if not tasks:
            failures = response.get("failures", [])
            return False, f"Task not found while checking completion: {failures}"

        task = tasks[0]
        task_status = str(task.get("lastStatus", ""))
        if task_status != "STOPPED":
            time.sleep(poll_interval_seconds)
            continue

        return _task_completion_result(task)

    return False, f"Timed out waiting for task completion after {timeout_seconds} seconds."


def _task_completion_result(task: dict[str, Any]) -> tuple[bool, str]:
    """Convert ECS task details into a completion result."""
    target = _find_container(task.get("containers", []), SRE_AGENT_CONTAINER_NAME)
    if target is None:
        stopped_reason = str(task.get("stoppedReason", "task stopped"))
        return (
            False,
            "Task stopped before container "
            f"{SRE_AGENT_CONTAINER_NAME} was observed: {stopped_reason}",
        )

    exit_code = target.get("exitCode")
    reason = str(target.get("reason", "")).strip()
    if exit_code == 0:
        return True, "Diagnosis task completed successfully."
    if reason:
        return False, reason
    if exit_code is not None:
        return False, f"Container {SRE_AGENT_CONTAINER_NAME} exited with code {exit_code}."

    stopped_reason = str(task.get("stoppedReason", "task stopped"))
    return (
        False,
        f"Task stopped without an exit code for {SRE_AGENT_CONTAINER_NAME}: {stopped_reason}",
    )


def _find_container(containers: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    """Return a container by name from task container details."""
    for container in containers:
        if container.get("name") == name:
            return container
    return None
