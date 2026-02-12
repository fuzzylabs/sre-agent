"""User env file helpers for the CLI."""

import os
import re
from pathlib import Path

from sre_agent.cli.config import env_path


def load_env_values() -> dict[str, str]:
    """Load env file values and overlay environment variables.

    Returns:
        Combined env file and environment variable values.
    """
    values = read_env_file(env_path())
    for key, value in os.environ.items():
        if value:
            values[key] = value
    return values


def read_env_file(path: Path) -> dict[str, str]:
    """Read simple key/value pairs from an env file.

    Args:
        path: Path to the env file.

    Returns:
        Parsed key/value pairs.
    """
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def write_env_file(path: Path, updates: dict[str, str]) -> None:
    """Write updates to the env file.

    Args:
        path: Path to the env file.
        updates: Values to write into the file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    current = read_env_file(path)
    for key, value in updates.items():
        if value:
            current[key] = value
        elif key in current:
            current.pop(key, None)

    lines = []
    for key, value in current.items():
        safe_value = _escape_env_value(value)
        lines.append(f"{key}={safe_value}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _escape_env_value(value: str) -> str:
    """Escape a value for env output.

    Args:
        value: Value to escape.

    Returns:
        The escaped value.
    """
    if re.search(r"\s", value):
        return f'"{value}"'
    return value
