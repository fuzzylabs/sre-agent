"""Configuration setup for CLI runs."""

from dataclasses import dataclass

import questionary

from sre_agent.cli.configuration.models import CliConfig
from sre_agent.cli.configuration.options import (
    AWS_LOGGING_PLATFORM_CHOICES,
    CODE_REPOSITORY_PROVIDER_CHOICES,
    CODE_REPOSITORY_PROVIDER_GITHUB,
    DEPLOYMENT_PLATFORM_AWS,
    DEPLOYMENT_PLATFORM_CHOICES,
    LEGACY_SELECTION_ENV_KEYS,
    LOGGING_PLATFORM_CLOUDWATCH,
    MODEL_PROVIDER_ANTHROPIC,
    MODEL_PROVIDER_CHOICES,
    NOTIFICATION_PLATFORM_CHOICES,
    NOTIFICATION_PLATFORM_SLACK,
)
from sre_agent.cli.configuration.providers.aws import (
    build_aws_connection_inputs,
    validate_aws_connection,
)
from sre_agent.cli.configuration.store import load_config, save_config
from sre_agent.cli.env import load_env_values, write_env_file
from sre_agent.cli.presentation.console import console
from sre_agent.config.paths import env_path


@dataclass(frozen=True)
class _MissingConfigItem:
    """A missing configuration item and whether to show it in summary."""

    label: str
    visible: bool = True


@dataclass(frozen=True)
class _WizardSelections:
    """Selected providers and platforms from the configuration wizard."""

    model_provider: str
    notification_platform: str
    code_repository_provider: str
    deployment_platform: str
    logging_platform: str
    slack_channel_id: str | None


def ensure_required_config() -> CliConfig:
    """Ensure the required configuration is present.

    Returns:
        The configuration object.
    """
    config = load_config()
    env_values = load_env_values()
    missing_items = _find_missing_config_items(env_values, config)

    if not missing_items:
        console.print("[orange1]Configuration detected.[/orange1]")
        reuse = questionary.confirm("Reuse existing configuration?", default=True).ask()
        if reuse:
            return config
        console.print("[dim]Reconfiguring all settings.[/dim]")
        return _run_config_wizard(config, env_values, force_reconfigure=True)

    visible_missing_items = [item for item in missing_items if item.visible]

    console.print("[yellow]No configurations found[/yellow]")
    for item in visible_missing_items:
        console.print(f"[#e0e0e0]- {item.label}[/#e0e0e0]")

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
    """Prompt for required configuration and save it to the user env file.

    Args:
        config: Existing configuration values.
        env_values: Current environment values.
        force_reconfigure: Whether to ignore existing values.

    Returns:
        The updated configuration object.
    """
    env_file_path = env_path()
    updates: dict[str, str] = {}

    model_provider = _configure_model_provider(
        config,
        env_values,
        force_reconfigure,
        updates,
    )
    notification_platform, slack_channel_id = _configure_notification_platform(
        config,
        env_values,
        force_reconfigure,
        updates,
    )
    code_repository_provider = _configure_code_repository_provider(
        config,
        env_values,
        force_reconfigure,
        updates,
    )
    deployment_platform, logging_platform = _configure_deployment_platform(
        config,
        env_values,
        force_reconfigure,
        updates,
    )

    _clear_legacy_selection_env_keys(updates)

    write_env_file(env_file_path, updates)

    selections = _WizardSelections(
        model_provider=model_provider,
        notification_platform=notification_platform,
        code_repository_provider=code_repository_provider,
        deployment_platform=deployment_platform,
        logging_platform=logging_platform,
        slack_channel_id=slack_channel_id,
    )
    _persist_wizard_choices(
        config,
        selections,
        updates,
    )

    console.print(f"[green]Saved configuration to {env_file_path}[/green]")
    return config


def _configure_model_provider(
    config: CliConfig,
    env_values: dict[str, str],
    force_reconfigure: bool,
    updates: dict[str, str],
) -> str:
    """Prompt for model provider and required credentials."""
    model_provider = _prompt_choice(
        "Model provider:",
        config.integrations.model_provider,
        force_reconfigure,
        MODEL_PROVIDER_CHOICES,
        MODEL_PROVIDER_ANTHROPIC,
    )
    if model_provider == MODEL_PROVIDER_ANTHROPIC:
        updates["ANTHROPIC_API_KEY"] = _prompt_secret(
            "Anthropic API key:",
            env_values.get("ANTHROPIC_API_KEY"),
            force_reconfigure,
        )
    else:
        _clear_env_keys(updates, "ANTHROPIC_API_KEY")
    return model_provider


def _configure_notification_platform(
    config: CliConfig,
    env_values: dict[str, str],
    force_reconfigure: bool,
    updates: dict[str, str],
) -> tuple[str, str | None]:
    """Prompt for notification platform and required credentials."""
    notification_platform = _prompt_choice(
        "Messaging/notification platform:",
        config.integrations.notification_platform,
        force_reconfigure,
        NOTIFICATION_PLATFORM_CHOICES,
        NOTIFICATION_PLATFORM_SLACK,
    )
    if notification_platform != NOTIFICATION_PLATFORM_SLACK:
        _clear_env_keys(updates, "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID")
        return notification_platform, None

    updates["SLACK_BOT_TOKEN"] = _prompt_secret(
        "Slack bot token:",
        env_values.get("SLACK_BOT_TOKEN"),
        force_reconfigure,
    )
    slack_channel_id = _prompt_text(
        "Slack channel ID:",
        env_values.get("SLACK_CHANNEL_ID") or config.integrations.slack_channel_id,
        force_reconfigure,
    )
    updates["SLACK_CHANNEL_ID"] = slack_channel_id
    return notification_platform, slack_channel_id


def _configure_code_repository_provider(
    config: CliConfig,
    env_values: dict[str, str],
    force_reconfigure: bool,
    updates: dict[str, str],
) -> str:
    """Prompt for code repository provider and required credentials."""
    code_repository_provider = _prompt_choice(
        "Remote code repository:",
        config.integrations.code_repository_provider,
        force_reconfigure,
        CODE_REPOSITORY_PROVIDER_CHOICES,
        CODE_REPOSITORY_PROVIDER_GITHUB,
    )
    if code_repository_provider == CODE_REPOSITORY_PROVIDER_GITHUB:
        updates["GITHUB_PERSONAL_ACCESS_TOKEN"] = _prompt_secret(
            "GitHub token:",
            env_values.get("GITHUB_PERSONAL_ACCESS_TOKEN"),
            force_reconfigure,
        )
    else:
        _clear_env_keys(updates, "GITHUB_PERSONAL_ACCESS_TOKEN")
    return code_repository_provider


def _configure_deployment_platform(
    config: CliConfig,
    env_values: dict[str, str],
    force_reconfigure: bool,
    updates: dict[str, str],
) -> tuple[str, str]:
    """Prompt for deployment platform, logging platform, and AWS credentials."""
    deployment_platform = _prompt_choice(
        "Which platform is your application deployed on?",
        config.integrations.deployment_platform,
        force_reconfigure,
        DEPLOYMENT_PLATFORM_CHOICES,
        DEPLOYMENT_PLATFORM_AWS,
    )
    if deployment_platform != DEPLOYMENT_PLATFORM_AWS:
        return deployment_platform, config.integrations.logging_platform

    logging_platform = _prompt_choice(
        "Logging platform:",
        config.integrations.logging_platform,
        force_reconfigure,
        AWS_LOGGING_PLATFORM_CHOICES,
        LOGGING_PLATFORM_CLOUDWATCH,
    )
    _configure_aws_credentials(config, env_values, force_reconfigure, updates)
    _report_aws_connection_check(updates, env_values, config)
    return deployment_platform, logging_platform


def _configure_aws_credentials(
    config: CliConfig,
    env_values: dict[str, str],
    force_reconfigure: bool,
    updates: dict[str, str],
) -> None:
    """Prompt for AWS credentials and region."""
    use_profile = questionary.confirm(
        "Use AWS_PROFILE instead of access keys?",
        default=bool(env_values.get("AWS_PROFILE") or config.aws.profile),
    ).ask()
    if use_profile:
        _configure_aws_profile_credentials(config, env_values, force_reconfigure, updates)
    else:
        _configure_aws_access_key_credentials(env_values, force_reconfigure, updates)

    updates["AWS_REGION"] = _prompt_text(
        "AWS region:",
        env_values.get("AWS_REGION", config.aws.region),
        force_reconfigure,
    )


def _configure_aws_profile_credentials(
    config: CliConfig,
    env_values: dict[str, str],
    force_reconfigure: bool,
    updates: dict[str, str],
) -> None:
    """Prompt for AWS profile credentials."""
    updates["AWS_PROFILE"] = _prompt_text(
        "AWS_PROFILE:",
        env_values.get("AWS_PROFILE") or config.aws.profile,
        force_reconfigure,
    )
    _clear_env_keys(
        updates,
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    )


def _configure_aws_access_key_credentials(
    env_values: dict[str, str],
    force_reconfigure: bool,
    updates: dict[str, str],
) -> None:
    """Prompt for AWS access key credentials."""
    updates["AWS_PROFILE"] = _empty_env_value()
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
    updates["AWS_SESSION_TOKEN"] = session_token or _empty_env_value()


def _clear_legacy_selection_env_keys(updates: dict[str, str]) -> None:
    """Remove deprecated provider selection keys from the env file."""
    _clear_env_keys(updates, *LEGACY_SELECTION_ENV_KEYS)


def _clear_env_keys(updates: dict[str, str], *keys: str) -> None:
    """Set keys to empty values so the env writer removes them."""
    for key in keys:
        updates[key] = _empty_env_value()


def _empty_env_value() -> str:
    """Return a canonical empty env value."""
    return ""


def _persist_wizard_choices(
    config: CliConfig,
    selections: _WizardSelections,
    updates: dict[str, str],
) -> None:
    """Persist wizard choices to cached CLI config."""
    config.integrations.model_provider = selections.model_provider
    config.integrations.notification_platform = selections.notification_platform
    config.integrations.code_repository_provider = selections.code_repository_provider
    config.integrations.deployment_platform = selections.deployment_platform
    config.integrations.logging_platform = selections.logging_platform
    config.integrations.slack_channel_id = selections.slack_channel_id
    if selections.deployment_platform == DEPLOYMENT_PLATFORM_AWS:
        config.aws.region = updates["AWS_REGION"]
        config.aws.profile = updates["AWS_PROFILE"] or None
    save_config(config)


def _find_missing_config_items(
    env_values: dict[str, str],
    config: CliConfig,
) -> list[_MissingConfigItem]:
    """Return missing configuration items.

    Args:
        env_values: Current environment values.
        config: Existing configuration values.

    Returns:
        A list of missing configuration items.
    """
    missing: list[_MissingConfigItem] = []
    _append_model_missing_items(missing, env_values, config)
    _append_notification_missing_items(missing, env_values, config)
    _append_repository_missing_items(missing, env_values, config)
    _append_deployment_missing_items(missing, env_values, config)
    return missing


def _append_model_missing_items(
    missing: list[_MissingConfigItem],
    env_values: dict[str, str],
    config: CliConfig,
) -> None:
    """Append missing model configuration items."""
    model_provider_value = config.integrations.model_provider
    if not _is_supported_choice(model_provider_value, MODEL_PROVIDER_CHOICES):
        missing.append(_MissingConfigItem("Model provider"))
    model_provider = _normalise_choice(
        model_provider_value,
        MODEL_PROVIDER_CHOICES,
        MODEL_PROVIDER_ANTHROPIC,
    )
    if model_provider == MODEL_PROVIDER_ANTHROPIC and not env_values.get("ANTHROPIC_API_KEY"):
        missing.append(_MissingConfigItem("Anthropic API key", visible=False))


def _append_notification_missing_items(
    missing: list[_MissingConfigItem],
    env_values: dict[str, str],
    config: CliConfig,
) -> None:
    """Append missing notification configuration items."""
    notification_platform_value = config.integrations.notification_platform
    if not _is_supported_choice(notification_platform_value, NOTIFICATION_PLATFORM_CHOICES):
        missing.append(_MissingConfigItem("Messaging/notification platform"))
    notification_platform = _normalise_choice(
        notification_platform_value,
        NOTIFICATION_PLATFORM_CHOICES,
        NOTIFICATION_PLATFORM_SLACK,
    )
    if notification_platform != NOTIFICATION_PLATFORM_SLACK:
        return
    if not env_values.get("SLACK_BOT_TOKEN"):
        missing.append(_MissingConfigItem("Slack bot token", visible=False))
    if not env_values.get("SLACK_CHANNEL_ID") and not config.integrations.slack_channel_id:
        missing.append(_MissingConfigItem("Slack channel ID"))


def _append_repository_missing_items(
    missing: list[_MissingConfigItem],
    env_values: dict[str, str],
    config: CliConfig,
) -> None:
    """Append missing repository configuration items."""
    code_repository_provider_value = config.integrations.code_repository_provider
    if not _is_supported_choice(code_repository_provider_value, CODE_REPOSITORY_PROVIDER_CHOICES):
        missing.append(_MissingConfigItem("Remote code repository"))
    code_repository_provider = _normalise_choice(
        code_repository_provider_value,
        CODE_REPOSITORY_PROVIDER_CHOICES,
        CODE_REPOSITORY_PROVIDER_GITHUB,
    )
    if code_repository_provider == CODE_REPOSITORY_PROVIDER_GITHUB and not env_values.get(
        "GITHUB_PERSONAL_ACCESS_TOKEN"
    ):
        missing.append(_MissingConfigItem("GitHub token", visible=False))


def _append_deployment_missing_items(
    missing: list[_MissingConfigItem],
    env_values: dict[str, str],
    config: CliConfig,
) -> None:
    """Append missing deployment configuration items."""
    deployment_platform_value = config.integrations.deployment_platform
    if not _is_supported_choice(deployment_platform_value, DEPLOYMENT_PLATFORM_CHOICES):
        missing.append(_MissingConfigItem("Deployment platform"))
    deployment_platform = _normalise_choice(
        deployment_platform_value,
        DEPLOYMENT_PLATFORM_CHOICES,
        DEPLOYMENT_PLATFORM_AWS,
    )
    if deployment_platform != DEPLOYMENT_PLATFORM_AWS:
        return

    if not _is_supported_choice(config.integrations.logging_platform, AWS_LOGGING_PLATFORM_CHOICES):
        missing.append(_MissingConfigItem("Logging platform"))
    has_profile = bool(env_values.get("AWS_PROFILE") or config.aws.profile)
    has_keys = bool(env_values.get("AWS_ACCESS_KEY_ID") and env_values.get("AWS_SECRET_ACCESS_KEY"))
    if not (has_profile or has_keys):
        missing.append(_MissingConfigItem("AWS credentials (AWS_PROFILE or access keys)"))
    if not env_values.get("AWS_REGION") and not config.aws.region:
        missing.append(_MissingConfigItem("AWS region"))


def _prompt_choice(
    label: str,
    current: str | None,
    force_reconfigure: bool,
    choices: tuple[tuple[str, str], ...],
    fallback: str,
) -> str:
    """Prompt for a single choice value.

    Args:
        label: Prompt label for the choice.
        current: Current value if already set.
        force_reconfigure: Whether to ignore existing values.
        choices: Available display/value pairs.
        fallback: Default choice value.

    Returns:
        The selected value.
    """
    default = fallback if force_reconfigure else _normalise_choice(current, choices, fallback)
    selection = questionary.select(
        label,
        choices=[questionary.Choice(title=title, value=value) for title, value in choices],
        default=default,
    ).ask()
    if not selection:
        console.print("[yellow]Selection required.[/yellow]")
        return _prompt_choice(label, current, force_reconfigure, choices, fallback)
    return str(selection)


def _normalise_choice(
    value: str | None,
    choices: tuple[tuple[str, str], ...],
    fallback: str,
) -> str:
    """Return a supported value or a fallback.

    Args:
        value: Current or selected value.
        choices: Available display/value pairs.
        fallback: Value to use when the current value is unsupported.

    Returns:
        A supported choice value.
    """
    if _is_supported_choice(value, choices):
        return str(value)
    return fallback


def _is_supported_choice(value: str | None, choices: tuple[tuple[str, str], ...]) -> bool:
    """Return true when a value exists in a choice list.

    Args:
        value: Current or selected value.
        choices: Available display/value pairs.

    Returns:
        True when the value is one of the choice values.
    """
    if not value:
        return False
    return any(value == choice_value for _, choice_value in choices)


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


def _report_aws_connection_check(
    updates: dict[str, str],
    env_values: dict[str, str],
    config: CliConfig,
) -> None:
    """Check AWS credentials and display the current identity."""
    console.print("[cyan]Checking AWS connection...[/cyan]")
    connection_inputs = build_aws_connection_inputs(updates, env_values, config)
    result = validate_aws_connection(connection_inputs)
    if result.success:
        console.print(f"[green]{result.message}[/green]")
        return

    console.print(f"[yellow]AWS connection check failed: {result.message}[/yellow]")
    console.print(
        "[dim]You can continue, but deployment and diagnostics will fail "
        "until credentials are fixed.[/dim]"
    )
