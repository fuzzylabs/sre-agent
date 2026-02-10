"""Deployment status checks for ECS."""

from typing import Any

from botocore.exceptions import ClientError

from sre_agent.core.deployments.aws_ecs.models import EcsDeploymentConfig


def check_deployment(session: Any, config: EcsDeploymentConfig) -> dict[str, str]:
    """Check whether deployment resources exist."""
    results: dict[str, str] = {}

    results["VPC"] = _check_vpc(session, config.vpc_id)
    results["Private subnets"] = _check_subnets(session, config.private_subnet_ids)
    results["Security group"] = _check_security_group(session, config.security_group_id)
    results["Secrets"] = _check_secrets(
        session,
        [
            config.secret_anthropic_name,
            config.secret_slack_bot_name,
            config.secret_github_token_name,
        ],
    )
    results["IAM roles"] = _check_roles(session, config)
    results["ECR repositories"] = _check_ecr_repos(
        session,
        [config.ecr_repo_sre_agent, config.ecr_repo_slack_mcp],
    )
    results["Log group"] = _check_log_group(session, config.log_group_name)
    results["Task definition"] = _check_task_definition(session, config.task_definition_arn)
    results["ECS cluster"] = _check_cluster(session, config.cluster_name)

    return results


def _check_vpc(session: Any, vpc_id: str | None) -> str:
    if not vpc_id:
        return "not set"
    ec2 = session.client("ec2")
    try:
        ec2.describe_vpcs(VpcIds=[vpc_id])
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "InvalidVpcID.NotFound":
            return "missing"
        return f"error: {code}"
    return "present"


def _check_subnets(session: Any, subnet_ids: list[str]) -> str:
    if not subnet_ids:
        return "not set"
    ec2 = session.client("ec2")
    missing = 0
    for subnet_id in subnet_ids:
        try:
            ec2.describe_subnets(SubnetIds=[subnet_id])
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code == "InvalidSubnetID.NotFound":
                missing += 1
            else:
                return f"error: {code}"
    if missing == 0:
        return "present"
    return f"missing {missing}/{len(subnet_ids)}"


def _check_security_group(session: Any, group_id: str | None) -> str:
    if not group_id:
        return "not set"
    ec2 = session.client("ec2")
    try:
        ec2.describe_security_groups(GroupIds=[group_id])
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "InvalidGroup.NotFound":
            return "missing"
        return f"error: {code}"
    return "present"


def _check_secrets(session: Any, names: list[str]) -> str:
    client = session.client("secretsmanager")
    missing = 0
    for name in names:
        try:
            client.describe_secret(SecretId=name)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code == "ResourceNotFoundException":
                missing += 1
            else:
                return f"error: {code}"
    if missing == 0:
        return "present"
    return f"missing {missing}/{len(names)}"


def _check_roles(session: Any, config: EcsDeploymentConfig) -> str:
    iam = session.client("iam")
    role_names = {
        f"{config.project_name}-task-execution",
        f"{config.project_name}-task",
    }
    missing = 0
    for role_name in role_names:
        try:
            iam.get_role(RoleName=role_name)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code == "NoSuchEntity":
                missing += 1
            else:
                return f"error: {code}"
    if missing == 0:
        return "present"
    return f"missing {missing}/{len(role_names)}"


def _check_ecr_repos(session: Any, names: list[str]) -> str:
    ecr = session.client("ecr")
    missing = 0
    for name in names:
        try:
            ecr.describe_repositories(repositoryNames=[name])
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code == "RepositoryNotFoundException":
                missing += 1
            else:
                return f"error: {code}"
    if missing == 0:
        return "present"
    return f"missing {missing}/{len(names)}"


def _check_log_group(session: Any, log_group_name: str) -> str:
    logs = session.client("logs")
    response = logs.describe_log_groups(logGroupNamePrefix=log_group_name)
    groups = [group["logGroupName"] for group in response.get("logGroups", [])]
    return "present" if log_group_name in groups else "missing"


def _check_task_definition(session: Any, task_definition_arn: str | None) -> str:
    if not task_definition_arn:
        return "not set"
    ecs = session.client("ecs")
    try:
        ecs.describe_task_definition(taskDefinition=task_definition_arn)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"ClientException", "InvalidParameterException"}:
            return "missing"
        return f"error: {code}"
    return "present"


def _check_cluster(session: Any, cluster_name: str) -> str:
    ecs = session.client("ecs")
    response = ecs.describe_clusters(clusters=[cluster_name])
    clusters = response.get("clusters", [])
    if not clusters:
        return "missing"
    if clusters[0].get("status") != "ACTIVE":
        return f"status {clusters[0].get('status')}"
    return "present"
