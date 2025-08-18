"""Configuration management for SRE Agent CLI."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


class ConfigError(Exception):
    """Configuration related errors."""

    pass


@dataclass
class SREAgentConfig:
    """SRE Agent configuration."""

    # API Configuration
    api_url: str = "http://localhost:8003"
    bearer_token: Optional[str] = None

    # Default settings
    default_cluster: Optional[str] = None
    default_namespace: str = "default"
    default_timeout: int = 300

    # Output preferences
    output_format: str = "rich"  # rich, json, plain
    verbose: bool = False

    # Monitoring settings
    monitor_interval: int = 30
    max_log_lines: int = 100


def get_config_path(custom_path: Optional[str] = None) -> Path:
    """Get the configuration file path."""
    if custom_path:
        return Path(custom_path)

    # Try common config locations
    config_locations = [
        Path.cwd() / ".sre-agent.json",
        Path.home() / ".config" / "sre-agent" / "config.json",
        Path.home() / ".sre-agent.json",
    ]

    for path in config_locations:
        if path.exists():
            return path

    # Default to home directory
    return Path.home() / ".sre-agent.json"


def load_config(config_path: Optional[str] = None) -> SREAgentConfig:
    """Load configuration from file."""
    path = get_config_path(config_path)

    if not path.exists():
        # Try to load from environment
        config = SREAgentConfig()

        # Load from environment variables
        if bearer_token := os.getenv("SRE_AGENT_TOKEN"):
            config.bearer_token = bearer_token
        if api_url := os.getenv("SRE_AGENT_API_URL"):
            config.api_url = api_url
        if default_cluster := os.getenv("SRE_AGENT_DEFAULT_CLUSTER"):
            config.default_cluster = default_cluster
        if default_namespace := os.getenv("SRE_AGENT_DEFAULT_NAMESPACE"):
            config.default_namespace = default_namespace

        return config

    try:
        with open(path) as f:
            data = json.load(f)

        return SREAgentConfig(**data)
    except (json.JSONDecodeError, TypeError) as e:
        raise ConfigError(f"Invalid configuration file: {e}")
    except FileNotFoundError:
        raise ConfigError(f"Configuration file not found: {path}")


def save_config(config: SREAgentConfig, config_path: Optional[str] = None) -> None:
    """Save configuration to file."""
    path = get_config_path(config_path)

    # Create directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, "w") as f:
            json.dump(asdict(config), f, indent=2)
    except Exception as e:
        raise ConfigError(f"Failed to save configuration: {e}")


def get_bearer_token_from_env() -> Optional[str]:
    """Get bearer token from .env file or environment."""
    # Try to read from .env file first
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()  # noqa: PLW2901
                    if line.startswith("DEV_BEARER_TOKEN="):
                        return line.split("=", 1)[1].strip("\"'")
        except Exception:
            pass

    # Fall back to environment variables
    return os.getenv("DEV_BEARER_TOKEN") or os.getenv("SRE_AGENT_TOKEN")
