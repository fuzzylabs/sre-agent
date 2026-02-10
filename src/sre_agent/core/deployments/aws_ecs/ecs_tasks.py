"""ECS task and cluster helpers."""

import time
from collections.abc import Callable
from typing import Any, cast

from botocore.exceptions import ClientError

from sre_agent.core.deployments.aws_ecs.models import EcsDeploymentConfig

SLACK_MCP_IMAGE = "ghcr.io/korotovsky/slack-mcp-server:latest"
HEALTH_CHECK_COMMAND = (
    'python -c "import urllib.request; '
    "urllib.request.urlopen('http://localhost:8000/health')\" "
    "> /dev/null 2>&1 || exit 1"
)


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
            "name": "sre-agent",
            "image": f"{config.ecr_sre_agent_uri}:{config.image_tag}",
            "essential": True,
            "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
            "healthCheck": {
                "command": [
                    "CMD-SHELL",
                    HEALTH_CHECK_COMMAND,
                ],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 20,
            },
            "environment": [
                {"name": "AWS_REGION", "value": config.aws_region},
                {"name": "MODEL", "value": config.model},
                {"name": "SLACK_CHANNEL_ID", "value": config.slack_channel_id},
                {"name": "SLACK_MCP_URL", "value": slack_mcp_url},
                {"name": "GITHUB_MCP_URL", "value": config.github_mcp_url},
                {
                    "name": "API_IDLE_TIMEOUT_SECONDS",
                    "value": str(config.api_idle_timeout_seconds),
                },
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
            "portMappings": [{"containerPort": config.slack_mcp_port, "protocol": "tcp"}],
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
    cluster_name: str,
    task_definition_arn: str,
    subnet_ids: list[str],
    security_group_id: str,
) -> str:
    """Run a one-off ECS task."""
    ecs = session.client("ecs")
    try:
        response = ecs.run_task(
            cluster=cluster_name,
            launchType="FARGATE",
            taskDefinition=task_definition_arn,
            count=1,
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": subnet_ids,
                    "securityGroups": [security_group_id],
                    "assignPublicIp": "DISABLED",
                }
            },
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "ClusterNotFoundException":
            raise RuntimeError(
                f"ECS cluster '{cluster_name}' is missing or inactive. "
                "Re-run deployment to recreate it."
            ) from exc
        raise RuntimeError(f"Failed to run ECS task: {exc}") from exc

    tasks = response.get("tasks", [])
    if not tasks:
        failures = response.get("failures", [])
        raise RuntimeError(f"Failed to run task: {failures}")
    return cast(str, tasks[0]["taskArn"])


def wait_for_api_health(
    session: Any,
    cluster_name: str,
    task_arn: str,
    timeout_seconds: int = 180,
    poll_interval_seconds: int = 5,
) -> tuple[bool, str]:
    """Wait for the API container health check to pass."""
    ecs = session.client("ecs")
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        response = ecs.describe_tasks(cluster=cluster_name, tasks=[task_arn])
        tasks = response.get("tasks", [])
        if not tasks:
            failures = response.get("failures", [])
            return False, f"Task not found while checking health: {failures}"

        task = tasks[0]
        task_status = str(task.get("lastStatus", ""))
        if task_status == "STOPPED":
            stop_reason = str(task.get("stoppedReason", "task stopped"))
            return False, stop_reason

        containers = task.get("containers", [])
        for container in containers:
            if container.get("name") != "sre-agent":
                continue

            container_status = str(container.get("lastStatus", ""))
            health_status = str(container.get("healthStatus", "UNKNOWN"))
            if health_status == "HEALTHY":
                return True, "API /health endpoint reported healthy."
            if health_status == "UNHEALTHY":
                reason = str(container.get("reason", "container reported unhealthy"))
                return False, reason
            if container_status == "STOPPED":
                reason = str(container.get("reason", "sre-agent container stopped"))
                return False, reason

        time.sleep(poll_interval_seconds)

    return False, f"Timed out waiting for API health after {timeout_seconds} seconds."


def stop_task(session: Any, cluster_name: str, task_arn: str, reason: str) -> None:
    """Stop a running ECS task."""
    ecs = session.client("ecs")
    try:
        ecs.stop_task(cluster=cluster_name, task=task_arn, reason=reason)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        message = str(exc.response.get("Error", {}).get("Message", "")).lower()
        if code in {"InvalidParameterException", "ClientException"} and "stopped" in message:
            return
        raise RuntimeError(f"Failed to stop task {task_arn}: {exc}") from exc
