"""AWS ECS remote deployment error helpers for the CLI."""

from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
    ProfileNotFound,
)

from sre_agent.cli.ui import console


def report_remote_error(exc: Exception) -> None:
    """Render remote deployment errors with actionable guidance.

    Args:
        exc: Raised exception from a remote deployment action.
    """
    if is_aws_auth_error(exc):
        console.print(
            "[red]AWS authentication failed. Your credentials are missing, invalid, "
            "or expired.[/red]"
        )
        console.print(
            "[dim]If using AWS profile/SSO, run: aws sso login --profile <profile>. "
            "If using temporary keys, refresh AWS_SESSION_TOKEN and retry.[/dim]"
        )
        return

    if is_aws_endpoint_error(exc):
        console.print("[red]Could not reach AWS endpoint from this environment.[/red]")
        console.print("[dim]Check network connectivity and AWS region configuration.[/dim]")
        return

    console.print(f"[red]Remote deployment failed: {exc}[/red]")


def is_aws_auth_error(exc: Exception) -> bool:
    """Return true when an exception chain indicates AWS auth issues.

    Args:
        exc: Raised exception from a remote deployment action.

    Returns:
        True when the chain contains an auth-related error.
    """
    auth_codes = {
        "ExpiredToken",
        "ExpiredTokenException",
        # spellchecker:ignore-next-line
        "UnrecognizedClientException",
        "InvalidClientTokenId",
        "InvalidSignatureException",
        "AccessDenied",
        "AccessDeniedException",
    }
    for item in exception_chain(exc):
        if isinstance(item, (NoCredentialsError, ProfileNotFound)):
            return True
        if isinstance(item, ClientError):
            code = str(item.response.get("Error", {}).get("Code", ""))
            if code in auth_codes:
                return True
        text = str(item)
        if "security token included in the request is expired" in text.lower():
            return True
    return False


def is_aws_endpoint_error(exc: Exception) -> bool:
    """Return true when an exception chain indicates endpoint/network errors.

    Args:
        exc: Raised exception from a remote deployment action.

    Returns:
        True when the chain contains endpoint connection errors.
    """
    return any(isinstance(item, EndpointConnectionError) for item in exception_chain(exc))


def exception_chain(exc: BaseException) -> list[BaseException]:
    """Return exceptions in cause/context chain.

    Args:
        exc: Root exception.

    Returns:
        Ordered exception chain from root to cause/context.
    """
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        chain.append(current)
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return chain
