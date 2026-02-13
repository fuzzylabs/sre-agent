"""AWS configuration helpers for CLI setup."""

from collections.abc import Mapping
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from sre_agent.cli.state import CliConfig


@dataclass(frozen=True)
class AwsConnectionInputs:
    """AWS values used to validate account access."""

    region: str | None
    profile: str | None
    access_key_id: str | None
    secret_access_key: str | None
    session_token: str | None


@dataclass(frozen=True)
class AwsConnectionCheckResult:
    """Result of an AWS connection check."""

    success: bool
    message: str


def build_aws_connection_inputs(
    updates: Mapping[str, str],
    env_values: Mapping[str, str],
    config: CliConfig,
) -> AwsConnectionInputs:
    """Resolve AWS connection inputs from wizard and existing values.

    Args:
        updates: Values captured in the current setup wizard run.
        env_values: Existing values from env file and process environment.
        config: Cached CLI configuration values.

    Returns:
        The resolved AWS connection inputs.
    """
    region = _resolve_env_value("AWS_REGION", updates, env_values, config.aws_region)
    profile = _resolve_env_value("AWS_PROFILE", updates, env_values, config.aws_profile)
    access_key_id = _resolve_env_value("AWS_ACCESS_KEY_ID", updates, env_values)
    secret_access_key = _resolve_env_value("AWS_SECRET_ACCESS_KEY", updates, env_values)
    session_token = _resolve_env_value("AWS_SESSION_TOKEN", updates, env_values)

    return AwsConnectionInputs(
        region=region,
        profile=profile,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        session_token=session_token,
    )


def validate_aws_connection(inputs: AwsConnectionInputs) -> AwsConnectionCheckResult:
    """Validate AWS access by calling STS get_caller_identity.

    Args:
        inputs: AWS connection inputs to validate.

    Returns:
        The connection check result.
    """
    try:
        session = _create_aws_session(inputs)
        identity = session.client("sts").get_caller_identity()
    except ProfileNotFound as exc:
        return AwsConnectionCheckResult(success=False, message=f"Profile not found: {exc}")
    except NoCredentialsError as exc:
        return AwsConnectionCheckResult(success=False, message=f"No AWS credentials found: {exc}")
    except ClientError as exc:
        return AwsConnectionCheckResult(success=False, message=str(exc))
    except Exception as exc:  # noqa: BLE001
        return AwsConnectionCheckResult(success=False, message=str(exc))

    account = str(identity.get("Account", "unknown-account"))
    arn = str(identity.get("Arn", "unknown-arn"))
    return AwsConnectionCheckResult(
        success=True,
        message=f"AWS connection successful. Account: {account}, Identity: {arn}",
    )


def _resolve_env_value(
    key: str,
    updates: Mapping[str, str],
    env_values: Mapping[str, str],
    fallback: str | None = None,
) -> str | None:
    """Read a value from updates first, then env values.

    Args:
        key: Name of the environment key.
        updates: Values captured in the current setup wizard run.
        env_values: Existing values from env file and process environment.
        fallback: Value to use when key is absent in updates and env values.

    Returns:
        The resolved value, if any.
    """
    if key in updates:
        return updates[key] or None
    return env_values.get(key) or fallback


def _create_aws_session(inputs: AwsConnectionInputs) -> boto3.session.Session:
    """Create an AWS session from resolved connection inputs.

    Args:
        inputs: AWS connection inputs.

    Returns:
        A boto3 session configured for the provided inputs.
    """
    if inputs.profile:
        return boto3.session.Session(
            profile_name=inputs.profile,
            region_name=inputs.region,
        )
    if inputs.access_key_id and inputs.secret_access_key:
        return boto3.session.Session(
            aws_access_key_id=inputs.access_key_id,
            aws_secret_access_key=inputs.secret_access_key,
            aws_session_token=inputs.session_token,
            region_name=inputs.region,
        )
    return boto3.session.Session(region_name=inputs.region)
