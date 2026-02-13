"""ECR helpers for ECS deployment."""

from typing import cast

from boto3.session import Session
from botocore.exceptions import ClientError


def ensure_repository(session: Session, name: str) -> str:
    """Ensure an ECR repository exists and return its URI."""
    ecr = session.client("ecr")
    try:
        response = ecr.describe_repositories(repositoryNames=[name])
        return cast(str, response["repositories"][0]["repositoryUri"])
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code != "RepositoryNotFoundException":
            raise RuntimeError(f"Failed to read ECR repo {name}: {exc}") from exc

    response = ecr.create_repository(repositoryName=name)
    return cast(str, response["repository"]["repositoryUri"])
