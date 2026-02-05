"""ECS task and cluster helpers."""

from collections.abc import Callable
from typing import Any, cast

from botocore.exceptions import ClientError

from sre_agent.core.deployments.aws_ecs.models import EcsDeploymentConfig


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
    if not config.exec_role_arn or not config.task_role_arn:
        raise RuntimeError("Task roles must be created before registering the task definition.")
    if not config.ecr_sre_agent_uri or not config.ecr_slack_mcp_uri:
        raise RuntimeError(
            "ECR repositories must be created before registering the task definition."
        )
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
            "image": f"{config.ecr_slack_mcp_uri}:{config.image_tag}",
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
        cpu=str(config.task_cpu),
        memory=str(config.task_memory),
        executionRoleArn=config.exec_role_arn,
        taskRoleArn=config.task_role_arn,
        containerDefinitions=container_definitions,
    )
    return cast(str, response["taskDefinition"]["taskDefinitionArn"])


def ensure_cluster(session: Any, cluster_name: str) -> str:
    """Ensure an ECS cluster exists."""
    ecs = session.client("ecs")
    response = ecs.describe_clusters(clusters=[cluster_name])
    clusters = response.get("clusters", [])
    if clusters:
        return cast(str, clusters[0]["clusterArn"])

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
    tasks = response.get("tasks", [])
    if not tasks:
        failures = response.get("failures", [])
        raise RuntimeError(f"Failed to run task: {failures}")
    return cast(str, tasks[0]["taskArn"])
