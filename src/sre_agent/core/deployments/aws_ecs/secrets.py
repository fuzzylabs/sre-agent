"""Secrets Manager helpers for ECS deployment."""

from dataclasses import dataclass
from typing import Any, cast

from botocore.exceptions import ClientError


@dataclass(frozen=True)
class SecretInfo:
    """Metadata about a Secrets Manager secret."""

    arn: str
    scheduled_for_deletion: bool


def get_secret_info(session: Any, name: str) -> SecretInfo | None:
    """Fetch secret metadata by name."""
    client = session.client("secretsmanager")
    try:
        response = client.describe_secret(SecretId=name)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "ResourceNotFoundException":
            return None
        raise RuntimeError(f"Failed to read secret {name}: {exc}") from exc

    deleted_date = response.get("DeletedDate")
    return SecretInfo(
        arn=cast(str, response["ARN"]),
        scheduled_for_deletion=deleted_date is not None,
    )


def create_secret(session: Any, name: str, value: str) -> str:
    """Create a secret and return its ARN."""
    client = session.client("secretsmanager")
    try:
        response = client.create_secret(Name=name, SecretString=value)
    except ClientError as exc:
        raise RuntimeError(f"Failed to create secret {name}: {exc}") from exc
    return cast(str, response["ARN"])


def restore_secret(session: Any, name: str) -> str:
    """Restore a secret that is scheduled for deletion."""
    client = session.client("secretsmanager")
    try:
        response = client.restore_secret(SecretId=name)
    except ClientError as exc:
        raise RuntimeError(f"Failed to restore secret {name}: {exc}") from exc
    return cast(str, response["ARN"])
