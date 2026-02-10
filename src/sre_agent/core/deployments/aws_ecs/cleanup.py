"""Clean-up helpers for ECS deployment resources."""

import time
from collections.abc import Callable
from typing import Any

from botocore.exceptions import ClientError

from sre_agent.core.deployments.aws_ecs.models import EcsDeploymentConfig
from sre_agent.core.deployments.aws_ecs.session import create_session


def cleanup_resources(
    config: EcsDeploymentConfig,
    reporter: Callable[[str], None],
    force_delete_secrets: bool,
) -> None:
    """Clean up resources created for ECS deployment."""
    session = create_session(config)
    reporter("Stopping ECS tasks (if any)")
    _stop_tasks(session, config.cluster_name, reporter)

    if config.task_definition_arn:
        reporter("Deregistering task definition")
        _deregister_task_definition(session, config.task_definition_arn, reporter)

    reporter("Deleting ECS cluster (if it exists)")
    _delete_cluster(session, config.cluster_name, reporter)

    if config.log_group_name:
        reporter("Deleting CloudWatch log group")
        _delete_log_group(session, config.log_group_name, reporter)

    reporter("Deleting ECR repositories (if they exist)")
    _delete_ecr_repo(session, config.ecr_repo_sre_agent, reporter)
    _delete_ecr_repo(session, config.ecr_repo_slack_mcp, reporter)

    reporter("Deleting IAM roles (if they exist)")
    _delete_roles(session, config, reporter)

    reporter("Deleting Secrets Manager secrets (if they exist)")
    _delete_secret(session, config.secret_anthropic_name, force_delete_secrets, reporter)
    _delete_secret(session, config.secret_slack_bot_name, force_delete_secrets, reporter)
    _delete_secret(session, config.secret_github_token_name, force_delete_secrets, reporter)

    if config.vpc_id:
        reporter("Deleting VPC resources")
        _cleanup_vpc(session, config.vpc_id, reporter)


def _stop_tasks(session: Any, cluster_name: str, reporter: Callable[[str], None]) -> None:
    """Stop running ECS tasks in the cluster."""
    ecs = session.client("ecs")
    try:
        response = ecs.list_tasks(cluster=cluster_name)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "ClusterNotFoundException":
            return
        raise RuntimeError(f"Failed to list ECS tasks: {exc}") from exc

    task_arns = response.get("taskArns", [])
    for task_arn in task_arns:
        reporter(f"Stopping task {task_arn}")
        try:
            ecs.stop_task(cluster=cluster_name, task=task_arn, reason="Clean up")
        except ClientError as exc:
            reporter(f"Failed to stop task {task_arn}: {exc}")


def _deregister_task_definition(
    session: Any,
    task_definition_arn: str,
    reporter: Callable[[str], None],
) -> None:
    """Deregister an ECS task definition."""
    ecs = session.client("ecs")
    try:
        ecs.deregister_task_definition(taskDefinition=task_definition_arn)
    except ClientError as exc:
        reporter(f"Failed to deregister task definition: {exc}")


def _delete_cluster(session: Any, cluster_name: str, reporter: Callable[[str], None]) -> None:
    """Delete an ECS cluster if it exists."""
    ecs = session.client("ecs")
    try:
        ecs.delete_cluster(cluster=cluster_name)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"ClusterNotFoundException"}:
            return
        reporter(f"Failed to delete cluster: {exc}")


def _delete_log_group(session: Any, log_group_name: str, reporter: Callable[[str], None]) -> None:
    """Delete a CloudWatch log group."""
    logs = session.client("logs")
    try:
        logs.delete_log_group(logGroupName=log_group_name)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code != "ResourceNotFoundException":
            reporter(f"Failed to delete log group: {exc}")


def _delete_ecr_repo(session: Any, name: str, reporter: Callable[[str], None]) -> None:
    """Delete an ECR repository if it exists."""
    if not name:
        return
    ecr = session.client("ecr")
    try:
        ecr.delete_repository(repositoryName=name, force=True)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code != "RepositoryNotFoundException":
            reporter(f"Failed to delete ECR repo {name}: {exc}")


def _delete_roles(
    session: Any,
    config: EcsDeploymentConfig,
    reporter: Callable[[str], None],
) -> None:
    """Delete IAM roles created for ECS tasks."""
    iam = session.client("iam")
    role_names = _role_names(config)
    for role_name in role_names:
        reporter(f"Removing IAM role {role_name}")
        _detach_managed_policies(iam, role_name, reporter)
        _delete_inline_policies(iam, role_name, reporter)
        try:
            iam.delete_role(RoleName=role_name)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code != "NoSuchEntity":
                reporter(f"Failed to delete role {role_name}: {exc}")


def _role_names(config: EcsDeploymentConfig) -> set[str]:
    """Return role names for clean-up."""
    names = set()
    if config.exec_role_arn:
        names.add(config.exec_role_arn.split("/")[-1])
    if config.task_role_arn:
        names.add(config.task_role_arn.split("/")[-1])
    names.add(f"{config.project_name}-task-execution")
    names.add(f"{config.project_name}-task")
    return names


def _detach_managed_policies(iam: Any, role_name: str, reporter: Callable[[str], None]) -> None:
    """Detach managed policies from a role."""
    try:
        response = iam.list_attached_role_policies(RoleName=role_name)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "NoSuchEntity":
            return
        reporter(f"Failed to list attached policies for {role_name}: {exc}")
        return

    for policy in response.get("AttachedPolicies", []):
        policy_arn = policy["PolicyArn"]
        try:
            iam.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        except ClientError as exc:
            reporter(f"Failed to detach policy {policy_arn} from {role_name}: {exc}")


def _delete_inline_policies(iam: Any, role_name: str, reporter: Callable[[str], None]) -> None:
    """Delete inline policies for a role."""
    try:
        response = iam.list_role_policies(RoleName=role_name)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "NoSuchEntity":
            return
        reporter(f"Failed to list inline policies for {role_name}: {exc}")
        return

    for policy_name in response.get("PolicyNames", []):
        try:
            iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        except ClientError as exc:
            reporter(f"Failed to delete policy {policy_name} from {role_name}: {exc}")


def _delete_secret(
    session: Any,
    name: str,
    force_delete: bool,
    reporter: Callable[[str], None],
) -> None:
    """Delete a secret if it exists."""
    if not name:
        return
    secrets = session.client("secretsmanager")
    try:
        secrets.delete_secret(
            SecretId=name,
            ForceDeleteWithoutRecovery=force_delete,
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code != "ResourceNotFoundException":
            reporter(f"Failed to delete secret {name}: {exc}")


def _cleanup_vpc(session: Any, vpc_id: str, reporter: Callable[[str], None]) -> None:
    """Delete a VPC and its dependent resources."""
    ec2 = session.client("ec2")

    nat_gateways = _list_nat_gateways(ec2, vpc_id)
    allocation_ids = [allocation for _, allocation in nat_gateways if allocation]
    for nat_gateway_id, _ in nat_gateways:
        reporter(f"Deleting NAT gateway {nat_gateway_id}")
        ec2.delete_nat_gateway(NatGatewayId=nat_gateway_id)

    if nat_gateways:
        _wait_for_nat_gateways(ec2, [nat_id for nat_id, _ in nat_gateways], reporter)

    for allocation_id in allocation_ids:
        reporter(f"Releasing Elastic IP {allocation_id}")
        try:
            ec2.release_address(AllocationId=allocation_id)
        except ClientError as exc:
            reporter(f"Failed to release Elastic IP {allocation_id}: {exc}")

    igw_ids = _list_internet_gateways(ec2, vpc_id)
    for igw_id in igw_ids:
        reporter(f"Detaching and deleting internet gateway {igw_id}")
        try:
            ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
            ec2.delete_internet_gateway(InternetGatewayId=igw_id)
        except ClientError as exc:
            reporter(f"Failed to delete internet gateway {igw_id}: {exc}")

    _delete_route_tables(ec2, vpc_id, reporter)
    _delete_subnets(ec2, vpc_id, reporter)
    _delete_security_groups(ec2, vpc_id, reporter)

    reporter(f"Deleting VPC {vpc_id}")
    try:
        ec2.delete_vpc(VpcId=vpc_id)
    except ClientError as exc:
        reporter(f"Failed to delete VPC {vpc_id}: {exc}")


def _list_nat_gateways(ec2: Any, vpc_id: str) -> list[tuple[str, str | None]]:
    """Return NAT gateway IDs and allocation IDs."""
    response = ec2.describe_nat_gateways(Filter=[{"Name": "vpc-id", "Values": [vpc_id]}])
    gateways = []
    for nat_gateway in response.get("NatGateways", []):
        nat_id = nat_gateway["NatGatewayId"]
        allocation_id = None
        for address in nat_gateway.get("NatGatewayAddresses", []):
            allocation_id = address.get("AllocationId")
        gateways.append((nat_id, allocation_id))
    return gateways


def _wait_for_nat_gateways(ec2: Any, nat_ids: list[str], reporter: Callable[[str], None]) -> None:
    """Wait for NAT gateways to delete."""
    attempts = 30
    delay = 10
    for _ in range(attempts):
        response = ec2.describe_nat_gateways(NatGatewayIds=nat_ids)
        states = {gw["NatGatewayId"]: gw["State"] for gw in response.get("NatGateways", [])}
        if all(state == "deleted" for state in states.values()):
            return
        reporter("Waiting for NAT gateways to delete...")
        time.sleep(delay)


def _list_internet_gateways(ec2: Any, vpc_id: str) -> list[str]:
    """List internet gateways attached to a VPC."""
    response = ec2.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )
    return [igw["InternetGatewayId"] for igw in response.get("InternetGateways", [])]


def _delete_route_tables(ec2: Any, vpc_id: str, reporter: Callable[[str], None]) -> None:
    """Delete non-main route tables."""
    response = ec2.describe_route_tables(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    for route_table in response.get("RouteTables", []):
        associations = route_table.get("Associations", [])
        is_main = any(assoc.get("Main") for assoc in associations)
        for assoc in associations:
            assoc_id = assoc.get("RouteTableAssociationId")
            if assoc_id and not assoc.get("Main"):
                try:
                    ec2.disassociate_route_table(AssociationId=assoc_id)
                except ClientError as exc:
                    reporter(f"Failed to disassociate route table: {exc}")
        if is_main:
            continue
        try:
            ec2.delete_route_table(RouteTableId=route_table["RouteTableId"])
        except ClientError as exc:
            reporter(f"Failed to delete route table: {exc}")


def _delete_subnets(ec2: Any, vpc_id: str, reporter: Callable[[str], None]) -> None:
    """Delete all subnets in a VPC."""
    response = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    for subnet in response.get("Subnets", []):
        subnet_id = subnet["SubnetId"]
        try:
            ec2.delete_subnet(SubnetId=subnet_id)
        except ClientError as exc:
            reporter(f"Failed to delete subnet {subnet_id}: {exc}")


def _delete_security_groups(ec2: Any, vpc_id: str, reporter: Callable[[str], None]) -> None:
    """Delete non-default security groups in a VPC."""
    response = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    for group in response.get("SecurityGroups", []):
        if group.get("GroupName") == "default":
            continue
        group_id = group["GroupId"]
        try:
            ec2.delete_security_group(GroupId=group_id)
        except ClientError as exc:
            reporter(f"Failed to delete security group {group_id}: {exc}")
