"""CLI configuration persistence helpers."""

import json
from pathlib import Path

from pydantic import ValidationError

from sre_agent.cli.configuration.models import CliConfig
from sre_agent.config.paths import cli_config_path


class ConfigError(RuntimeError):
    """Configuration related errors."""


def load_config() -> CliConfig:
    """Load CLI configuration from disk.

    Returns:
        The loaded configuration object.
    """
    path = cli_config_path()
    if not path.exists():
        return CliConfig()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid configuration file: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError("Configuration file must contain a JSON object.")

    try:
        return CliConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration values: {exc}") from exc


def save_config(config: CliConfig) -> Path:
    """Save CLI configuration to disk.

    Args:
        config: Configuration object to save.

    Returns:
        The saved configuration file path.
    """
    path = cli_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path
