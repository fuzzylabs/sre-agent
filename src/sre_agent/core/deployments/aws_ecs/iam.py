"""IAM role helpers for ECS deployment."""

import json
from collections.abc import Callable
from typing import Any, cast

from botocore.exceptions import ClientError


def ensure_roles(
    session: Any,
    project_name: str,
    region: str,
    secret_arns: list[str],
    reporter: Callable[[str], None],
) -> tuple[str, str]:
    """Ensure execution and task roles exist."""
    if not secret_arns:
        raise RuntimeError("Secret ARNs are required before creating roles.")

    iam = session.client("iam")
    exec_role_name = f"{project_name}-task-execution"
    task_role_name = f"{project_name}-task"

    reporter("Ensuring task execution role")
    exec_role_arn = _ensure_role(iam, exec_role_name, _ecs_trust_policy())
    _attach_managed_policy(
        iam,
        exec_role_name,
        "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
    )
    _put_inline_policy(
        iam,
        exec_role_name,
        f"{project_name}-secrets",
        _secrets_policy(secret_arns),
    )

    reporter("Ensuring task role for CloudWatch access")
    task_role_arn = _ensure_role(iam, task_role_name, _ecs_trust_policy())
    account_id = _get_account_id(session)
    _put_inline_policy(
        iam,
        task_role_name,
        f"{project_name}-logs",
        _logs_policy(region, account_id),
    )

    return exec_role_arn, task_role_arn


def ensure_service_linked_role(session: Any, reporter: Callable[[str], None]) -> None:
    """Ensure the ECS service-linked role exists."""
    iam = session.client("iam")
    role_name = "AWSServiceRoleForECS"
    try:
        iam.get_role(RoleName=role_name)
        reporter("ECS service-linked role already exists")
        return
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code != "NoSuchEntity":
            raise RuntimeError(f"Failed to read service-linked role: {exc}") from exc

    reporter("Creating ECS service-linked role")
    try:
        iam.create_service_linked_role(AWSServiceName="ecs.amazonaws.com")
    except ClientError as exc:
        raise RuntimeError(f"Failed to create service-linked role: {exc}") from exc


def _ensure_role(iam: Any, role_name: str, trust_policy: dict[str, Any]) -> str:
    """Create a role if needed and return its ARN."""
    try:
        response = iam.get_role(RoleName=role_name)
        return cast(str, response["Role"]["Arn"])
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code != "NoSuchEntity":
            raise RuntimeError(f"Failed to read role {role_name}: {exc}") from exc

    response = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
    )
    return cast(str, response["Role"]["Arn"])


def _attach_managed_policy(iam: Any, role_name: str, policy_arn: str) -> None:
    """Attach a managed policy if it is missing."""
    response = iam.list_attached_role_policies(RoleName=role_name)
    attached = {policy["PolicyArn"] for policy in response.get("AttachedPolicies", [])}
    if policy_arn in attached:
        return
    iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)


def _put_inline_policy(
    iam: Any,
    role_name: str,
    policy_name: str,
    policy_doc: dict[str, Any],
) -> None:
    """Attach or update an inline policy."""
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_doc),
    )


def _ecs_trust_policy() -> dict[str, Any]:
    """Return the ECS task trust policy."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }


def _secrets_policy(secret_arns: list[str]) -> dict[str, Any]:
    """Allow read access to Secrets Manager."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": secret_arns,
            }
        ],
    }


def _logs_policy(region: str, account_id: str) -> dict[str, Any]:
    """Allow CloudWatch Logs queries."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["logs:FilterLogEvents"],
                "Resource": f"arn:aws:logs:{region}:{account_id}:log-group:*",
            }
        ],
    }


def _get_account_id(session: Any) -> str:
    """Return the AWS account ID."""
    client = session.client("sts")
    response = client.get_caller_identity()
    return cast(str, response["Account"])
