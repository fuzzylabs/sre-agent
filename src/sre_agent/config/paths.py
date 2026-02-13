"""Shared filesystem paths for user configuration."""

from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "sre-agent"
CLI_CONFIG_FILENAME = "config.json"
ENV_FILENAME = ".env"


def config_dir() -> Path:
    """Return the user configuration directory.

    Returns:
        The user configuration directory path.
    """
    return Path(user_config_dir(APP_NAME))


def cli_config_path() -> Path:
    """Return the CLI configuration file path.

    Returns:
        The CLI configuration file path.
    """
    return config_dir() / CLI_CONFIG_FILENAME


def env_path() -> Path:
    """Return the user env file path.

    Returns:
        The user env file path.
    """
    return config_dir() / ENV_FILENAME
