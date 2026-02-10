"""Docker build and push helpers."""

import base64
import shutil
import subprocess  # nosec B404
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

TARGET_PLATFORM = "linux/arm64"
TARGET_ECS_ARCHITECTURE = "ARM64"


@dataclass(frozen=True)
class ImageBuildConfig:
    """Image build settings for the ECS deployment."""

    sre_agent_uri: str
    image_tag: str


def build_and_push_images(
    session: Any,
    root_dir: Path,
    image_config: ImageBuildConfig,
    reporter: Callable[[str], None],
) -> str:
    """Build and push container images to ECR."""
    _require_docker()

    reporter("Authenticating Docker with ECR")
    username, password, proxy_endpoint = _ecr_login(session)
    _run(
        [
            "docker",
            "login",
            "--username",
            username,
            "--password-stdin",
            proxy_endpoint,
        ],
        reporter,
        input_bytes=password.encode("utf-8"),
    )

    reporter(f"Building and pushing sre-agent image ({TARGET_PLATFORM})")
    _run(
        [
            "docker",
            "build",
            "--platform",
            TARGET_PLATFORM,
            "-t",
            f"{image_config.sre_agent_uri}:{image_config.image_tag}",
            str(root_dir),
        ],
        reporter,
    )
    _run(
        ["docker", "push", f"{image_config.sre_agent_uri}:{image_config.image_tag}"],
        reporter,
    )

    reporter(f"Using ECS runtime CPU architecture: {TARGET_ECS_ARCHITECTURE}")
    return TARGET_ECS_ARCHITECTURE


def _require_docker() -> None:
    """Ensure Docker is installed."""
    if not shutil.which("docker"):
        raise RuntimeError("Docker is required to build and push images.")


def _ecr_login(session: Any) -> tuple[str, str, str]:
    """Return Docker login credentials for ECR."""
    ecr = session.client("ecr")
    try:
        # spellchecker:ignore-next-line
        response = ecr.get_authorization_token()
    except ClientError as exc:
        raise RuntimeError(f"Failed to authenticate with ECR: {exc}") from exc

    # spellchecker:ignore-next-line
    auth_data = response["authorizationData"][0]
    # spellchecker:ignore-next-line
    token = base64.b64decode(auth_data["authorizationToken"]).decode("utf-8")
    username, password = token.split(":", 1)
    proxy_endpoint = auth_data["proxyEndpoint"]
    return username, password, proxy_endpoint


def _run(
    command: list[str],
    reporter: Callable[[str], None],
    input_bytes: bytes | None = None,
) -> None:
    """Run a subprocess command."""
    executable = shutil.which(command[0])
    if not executable:
        raise RuntimeError(f"Executable not found: {command[0]}")
    resolved_command = [executable, *command[1:]]
    reporter(f"Running: {' '.join(resolved_command)}")
    subprocess.run(resolved_command, check=True, input=input_bytes)  # nosec B603
