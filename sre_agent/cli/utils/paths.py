"""Path utilities for SRE Agent CLI."""

import os
from importlib.resources import files
from pathlib import Path


def get_compose_file_path(dev_mode: bool = False) -> Path:
    """Get the path to the appropriate compose file.

    Args:
        dev_mode: If True, returns path to dev compose file

    Returns:
        Path to the compose file
    """
    filename = "compose.dev.yaml" if dev_mode else "compose.agent.yaml"

    # First, check if we're in development (files exist in current directory)
    local_file = Path.cwd() / filename
    if local_file.exists():
        return local_file

    # If not in development, extract from package
    try:
        if files is None:
            raise ImportError("importlib.resources not available")

        package_files = files("sre_agent")
        compose_file = package_files / filename

        # Extract to config directory alongside .env file
        config_dir = get_config_dir()
        target_path = config_dir / filename
        target_path.write_text(compose_file.read_text())
        return target_path

    except (ImportError, FileNotFoundError, AttributeError):
        # Fallback: look in current directory
        return Path.cwd() / filename


def get_env_file_path() -> Path:
    """Get the path to the .env file.

    Returns:
        Path to .env file in the user's config directory
    """
    return get_config_dir() / ".env"


def get_user_data_dir() -> Path:
    """Get user data directory for SRE Agent.

    Returns:
        Path to user data directory
    """
    if os.name == "nt":  # Windows
        data_dir = Path(os.environ.get("APPDATA", Path.home())) / "sre-agent"
    else:  # Unix-like
        data_dir = Path.home() / ".local" / "share" / "sre-agent"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_dir() -> Path:
    """Get configuration directory for SRE Agent.

    Returns:
        Path to config directory
    """
    if os.name == "nt":  # Windows
        config_dir = Path(os.environ.get("APPDATA", Path.home())) / "sre-agent"
    else:  # Unix-like
        config_dir = Path.home() / ".config" / "sre-agent"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
