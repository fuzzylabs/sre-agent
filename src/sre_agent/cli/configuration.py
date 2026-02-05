"""Configuration setup for CLI runs."""

import os
import re
from pathlib import Path

import questionary

from sre_agent.cli.config import CliConfig, load_config, save_config
from sre_agent.cli.mode.paths import project_root
from sre_agent.cli.ui import console


def ensure_required_config() -> CliConfig:
    """Ensure the required configuration is present.

    Returns:
        The configuration object.
    """
    config = load_config()
    env_values = _load_env_values()
    missing = _find_missing_config(env_values, config)

    if not missing:
        console.print("[green]Configuration detected.[/green]")
        reuse = questionary.confirm("Reuse existing configuration?", default=True).ask()
        if reuse:
            return config
        console.print("[dim]Reconfiguring all settings.[/dim]")
        return _run_config_wizard(config, env_values, force_reconfigure=True)

    console.print("[yellow]Configuration missing for:[/yellow]")
    for item in missing:
        console.print(f"- {item}")

    configure = questionary.confirm("Configure now?", default=True).ask()
    if not configure:
        console.print("[dim]Skipping configuration. Some features may fail.[/dim]")
        return config

    return _run_config_wizard(config, env_values, force_reconfigure=False)


def _run_config_wizard(
    config: CliConfig,
    env_values: dict[str, str],
    force_reconfigure: bool,
) -> CliConfig:
    """Prompt for required configuration and save it to .env.

    Args:
        config: Existing configuration values.
        env_values: Current environment values.
        force_reconfigure: Whether to ignore existing values.

    Returns:
        The updated configuration object.
    """
    env_path = project_root() / ".env"
    updates: dict[str, str] = {}

    updates["ANTHROPIC_API_KEY"] = _prompt_secret(
        "Anthropic API key:",
        env_values.get("ANTHROPIC_API_KEY"),
        force_reconfigure,
    )
    updates["SLACK_BOT_TOKEN"] = _prompt_secret(
        "Slack bot token:",
        env_values.get("SLACK_BOT_TOKEN"),
        force_reconfigure,
    )
    slack_channel_id = _prompt_text(
        "Slack channel ID:",
        env_values.get("SLACK_CHANNEL_ID"),
        force_reconfigure,
    )
    updates["SLACK_CHANNEL_ID"] = slack_channel_id
    updates["GITHUB_PERSONAL_ACCESS_TOKEN"] = _prompt_secret(
        "GitHub token:",
        env_values.get("GITHUB_PERSONAL_ACCESS_TOKEN"),
        force_reconfigure,
    )

    use_profile = questionary.confirm(
        "Use AWS_PROFILE instead of access keys?",
        default=bool(env_values.get("AWS_PROFILE")),
    ).ask()
    if use_profile:
        updates["AWS_PROFILE"] = _prompt_text(
            "AWS_PROFILE:",
            env_values.get("AWS_PROFILE"),
            force_reconfigure,
        )
    else:
        updates["AWS_ACCESS_KEY_ID"] = _prompt_text(
            "AWS access key ID:",
            env_values.get("AWS_ACCESS_KEY_ID"),
            force_reconfigure,
        )
        updates["AWS_SECRET_ACCESS_KEY"] = _prompt_secret(
            "AWS secret access key:",
            env_values.get("AWS_SECRET_ACCESS_KEY"),
            force_reconfigure,
        )
        session_token = questionary.password("AWS session token (optional):").ask()
        if session_token:
            updates["AWS_SESSION_TOKEN"] = session_token

    updates["AWS_REGION"] = _prompt_text(
        "AWS region:",
        env_values.get("AWS_REGION", config.aws_region),
        force_reconfigure,
    )

    _write_env_file(env_path, updates)

    config.slack_channel_id = slack_channel_id
    config.aws_region = updates["AWS_REGION"]
    save_config(config)

    console.print(f"[green]Saved configuration to {env_path}[/green]")
    return config


def _find_missing_config(env_values: dict[str, str], config: CliConfig) -> list[str]:
    """Return a list of missing configuration items.

    Args:
        env_values: Current environment values.
        config: Existing configuration values.

    Returns:
        A list of missing configuration labels.
    """
    missing = []
    if not env_values.get("ANTHROPIC_API_KEY"):
        missing.append("Anthropic API key")
    if not env_values.get("SLACK_BOT_TOKEN"):
        missing.append("Slack bot token")
    if not env_values.get("SLACK_CHANNEL_ID") and not config.slack_channel_id:
        missing.append("Slack channel ID")
    if not env_values.get("GITHUB_PERSONAL_ACCESS_TOKEN"):
        missing.append("GitHub token")

    has_profile = bool(env_values.get("AWS_PROFILE") or config.aws_profile)
    has_keys = bool(env_values.get("AWS_ACCESS_KEY_ID") and env_values.get("AWS_SECRET_ACCESS_KEY"))
    if not (has_profile or has_keys):
        missing.append("AWS credentials (AWS_PROFILE or access keys)")

    if not env_values.get("AWS_REGION") and not config.aws_region:
        missing.append("AWS region")

    return missing


def _prompt_secret(label: str, current: str | None, force_reconfigure: bool) -> str:
    """Prompt for a secret value.

    Args:
        label: Prompt label for the value.
        current: Current value if already set.
        force_reconfigure: Whether to ignore existing values.

    Returns:
        The selected secret value.
    """
    if current and not force_reconfigure:
        use_existing = questionary.confirm(f"{label} already set. Keep it?", default=True).ask()
        if use_existing:
            return current
    value: str | None = questionary.password(label).ask()
    if not value:
        console.print("[yellow]Value required.[/yellow]")
        return _prompt_secret(label, current, force_reconfigure)
    return value


def _prompt_text(label: str, current: str | None, force_reconfigure: bool) -> str:
    """Prompt for a text value.

    Args:
        label: Prompt label for the value.
        current: Current value if already set.
        force_reconfigure: Whether to ignore existing values.

    Returns:
        The selected text value.
    """
    default = "" if force_reconfigure else (current or "")
    value: str | None = questionary.text(label, default=default).ask()
    if not value:
        console.print("[yellow]Value required.[/yellow]")
        return _prompt_text(label, current, force_reconfigure)
    return value


def _load_env_values() -> dict[str, str]:
    """Load .env values and overlay environment variables.

    Returns:
        Combined .env and environment variable values.
    """
    env_path = project_root() / ".env"
    values = _read_env_file(env_path)
    for key, value in os.environ.items():
        if value:
            values[key] = value
    return values


def _read_env_file(path: Path) -> dict[str, str]:
    """Read simple key/value pairs from a .env file.

    Args:
        path: Path to the .env file.

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


def _write_env_file(path: Path, updates: dict[str, str]) -> None:
    """Write updates to the .env file.

    Args:
        path: Path to the .env file.
        updates: Values to write into the file.
    """
    current = _read_env_file(path)
    current.update({key: value for key, value in updates.items() if value})

    lines = []
    for key, value in current.items():
        safe_value = _escape_env_value(value)
        lines.append(f"{key}={safe_value}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _escape_env_value(value: str) -> str:
    """Escape a value for .env output.

    Args:
        value: Value to escape.

    Returns:
        The escaped value.
    """
    if re.search(r"\s", value):
        return f'"{value}"'
    return value
