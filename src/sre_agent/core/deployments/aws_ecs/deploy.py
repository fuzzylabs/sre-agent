"""Deployment entrypoint for ECS."""

from collections.abc import Callable

from sre_agent.core.deployments.aws_ecs.models import EcsDeploymentConfig
from sre_agent.core.deployments.aws_ecs.session import create_session, get_identity


def deploy_agent(config: EcsDeploymentConfig, reporter: Callable[[str], None]) -> None:
    """Deploy the SRE Agent to ECS."""
    reporter("Checking AWS credentials")
    session = create_session(config)
    identity = get_identity(session)
    reporter(f"Using AWS account {identity['Account']} ({identity['Arn']})")

    reporter("Deployment steps are not implemented yet.")
