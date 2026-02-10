"""AWS ECS deployment helpers."""

from sre_agent.core.deployments.aws_ecs.cleanup import cleanup_resources
from sre_agent.core.deployments.aws_ecs.deploy import deploy_agent
from sre_agent.core.deployments.aws_ecs.ecr import ensure_repository
from sre_agent.core.deployments.aws_ecs.ecs_tasks import (
    ensure_cluster,
    register_task_definition,
    run_task,
)
from sre_agent.core.deployments.aws_ecs.iam import ensure_roles, ensure_service_linked_role
from sre_agent.core.deployments.aws_ecs.images import ImageBuildConfig, build_and_push_images
from sre_agent.core.deployments.aws_ecs.models import (
    EcsDeploymentConfig,
    NetworkSelection,
    SecurityGroupInfo,
    SubnetInfo,
    VpcInfo,
)
from sre_agent.core.deployments.aws_ecs.network import (
    create_basic_vpc,
    list_private_subnets,
    list_vpcs,
)
from sre_agent.core.deployments.aws_ecs.secrets import create_secret, get_secret_arn
from sre_agent.core.deployments.aws_ecs.security_groups import (
    create_security_group,
    list_security_groups,
)
from sre_agent.core.deployments.aws_ecs.session import create_session, get_identity
from sre_agent.core.deployments.aws_ecs.status import check_deployment

__all__ = [
    "EcsDeploymentConfig",
    "NetworkSelection",
    "ImageBuildConfig",
    "SecurityGroupInfo",
    "SubnetInfo",
    "VpcInfo",
    "build_and_push_images",
    "cleanup_resources",
    "check_deployment",
    "create_basic_vpc",
    "create_security_group",
    "create_secret",
    "create_session",
    "deploy_agent",
    "ensure_cluster",
    "ensure_repository",
    "ensure_roles",
    "ensure_service_linked_role",
    "get_identity",
    "get_secret_arn",
    "list_private_subnets",
    "list_security_groups",
    "list_vpcs",
    "register_task_definition",
    "run_task",
]
