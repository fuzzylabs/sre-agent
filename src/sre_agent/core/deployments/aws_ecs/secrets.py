"""Secrets Manager helpers for ECS deployment."""

from typing import Any, cast

from botocore.exceptions import ClientError


def get_secret_arn(session: Any, name: str) -> str | None:
    """Fetch a secret ARN by name."""
    client = session.client("secretsmanager")
    try:
        response = client.describe_secret(SecretId=name)
        return cast(str, response["ARN"])
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "ResourceNotFoundException":
            return None
        raise RuntimeError(f"Failed to read secret {name}: {exc}") from exc


def create_secret(session: Any, name: str, value: str) -> str:
    """Create a secret and return its ARN."""
    client = session.client("secretsmanager")
    try:
        response = client.create_secret(Name=name, SecretString=value)
    except ClientError as exc:
        raise RuntimeError(f"Failed to create secret {name}: {exc}") from exc
    return cast(str, response["ARN"])
