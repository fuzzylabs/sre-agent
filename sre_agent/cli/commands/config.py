"""Configuration command for SRE Agent CLI.

Interactive configuration menu for all SRE Agent settings.
"""

import os
import shutil
import subprocess  # nosec B404
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


def _print_config_header() -> None:
    """Print the configuration menu header."""
    console.print(
        Panel(
            "[bold cyan]⚙️  SRE Agent Configuration Menu[/bold cyan]\n\n"
            "Configure your SRE Agent settings including AWS cluster, "
            "GitHub integration, Slack notifications, and LLM Firewall.",
            border_style="cyan",
            title="Configuration",
            title_align="center",
        )
    )


def _display_main_menu() -> str:
    """Display main configuration menu and get user choice."""
    console.print("\n[bold]Configuration Options:[/bold]")

    menu_table = Table(show_header=False, box=None, padding=(0, 1))
    menu_table.add_row("[cyan]1.[/cyan]", "AWS Kubernetes cluster configuration")
    menu_table.add_row("[cyan]2.[/cyan]", "GitHub integration settings")
    menu_table.add_row("[cyan]3.[/cyan]", "Slack configuration")
    menu_table.add_row("[cyan]4.[/cyan]", "LLM Firewall configuration")
    menu_table.add_row("[cyan]5.[/cyan]", "Model provider settings")
    menu_table.add_row("[cyan]6.[/cyan]", "View current configuration")
    menu_table.add_row("[cyan]7.[/cyan]", "Reset all configuration")
    menu_table.add_row("[cyan]8.[/cyan]", "Exit configuration menu")

    console.print(menu_table)

    return Prompt.ask(
        "\nSelect an option", choices=["1", "2", "3", "4", "5", "6", "7", "8"], default="1"
    )


def _update_env_file(updates: dict[str, str]) -> None:
    """Update the .env file with new values."""
    env_file = Path.cwd() / ".env"
    env_vars = {}

    if env_file.exists():
        with open(env_file) as f:
            for raw_line in f:
                line = raw_line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    env_vars[key] = value

    env_vars.update(updates)

    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    console.print(f"[green]✅ Configuration updated in {env_file}[/green]")


def _configure_aws_cluster() -> None:
    """Configure AWS Kubernetes cluster settings."""
    console.print(
        Panel(
            "[bold]AWS Kubernetes Cluster Configuration[/bold]\n\n"
            "Configure your EKS cluster connection and AWS credentials.",
            border_style="blue",
        )
    )

    # Check prerequisites
    if not shutil.which("aws"):
        console.print("[red]❌ AWS CLI is not installed.[/red]")
        console.print("Please install AWS CLI first:")
        console.print('   curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"')
        console.print("   sudo installer -pkg AWSCLIV2.pkg -target /")
        return

    if not shutil.which("kubectl"):
        console.print("[red]❌ kubectl is not installed.[/red]")
        console.print("Please install kubectl first:")
        console.print("   https://kubernetes.io/docs/tasks/tools/")
        return

    console.print("[green]✅ AWS CLI and kubectl are installed[/green]")

    # Get current values
    current_region = os.getenv("AWS_REGION", "")
    current_cluster = os.getenv("TARGET_EKS_CLUSTER_NAME", "")

    console.print(f"\nCurrent AWS Region: [cyan]{current_region or 'Not set'}[/cyan]")
    console.print(f"Current EKS Cluster: [cyan]{current_cluster or 'Not set'}[/cyan]")

    # Get new values
    region = Prompt.ask("AWS Region", default=current_region or "eu-west-2")
    cluster_name = Prompt.ask("EKS Cluster Name", default=current_cluster or "")

    if not cluster_name:
        console.print("[yellow]⚠️  No cluster name provided. Skipping.[/yellow]")
        return

    # Update environment
    _update_env_file({"AWS_REGION": region, "TARGET_EKS_CLUSTER_NAME": cluster_name})

    # Configure kubectl
    if Confirm.ask("Configure kubectl access to this cluster?", default=True):
        try:
            console.print(f"[cyan]Configuring kubectl for {cluster_name}...[/cyan]")
            result = subprocess.run(  # nosec B603 B607
                ["aws", "eks", "update-kubeconfig", "--region", region, "--name", cluster_name],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                console.print(f"[green]✅ kubectl configured for {cluster_name}[/green]")
            else:
                console.print(f"[red]❌ Failed to configure kubectl: {result.stderr}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Error configuring kubectl: {e}[/red]")


def _configure_github() -> None:
    """Configure GitHub integration settings."""
    console.print(
        Panel(
            "[bold]GitHub Integration Configuration[/bold]\n\n"
            "Configure GitHub access for issue creation and repository monitoring.",
            border_style="blue",
        )
    )

    # Get current values
    current_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    current_org = os.getenv("GITHUB_ORGANISATION", "")
    current_repo = os.getenv("GITHUB_REPO_NAME", "")
    current_project_root = os.getenv("PROJECT_ROOT", "")

    console.print(f"Current GitHub Token: [cyan]{'Set' if current_token else 'Not set'}[/cyan]")
    console.print(f"Current Organisation: [cyan]{current_org or 'Not set'}[/cyan]")
    console.print(f"Current Repository: [cyan]{current_repo or 'Not set'}[/cyan]")
    console.print(f"Current Project Root: [cyan]{current_project_root or 'Not set'}[/cyan]")

    console.print(
        "\n[dim]💡 Generate a personal access token at: https://github.com/settings/tokens[/dim]"
    )

    # Get new values
    token = Prompt.ask("GitHub Personal Access Token", password=True, default="")
    if not token and current_token:
        token = current_token

    org = Prompt.ask("GitHub Organisation", default=current_org or "")
    repo = Prompt.ask("Repository Name", default=current_repo or "")
    project_root = Prompt.ask("Project Root Path", default=current_project_root or "src")

    # Update environment
    updates = {}
    if token:
        updates["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
    if org:
        updates["GITHUB_ORGANISATION"] = org
    if repo:
        updates["GITHUB_REPO_NAME"] = repo
    if project_root:
        updates["PROJECT_ROOT"] = project_root

    if updates:
        _update_env_file(updates)


def _configure_slack() -> None:
    """Configure Slack integration settings."""
    console.print(
        Panel(
            "[bold]Slack Configuration[/bold]\n\n"
            "Configure Slack integration for notifications and bot interactions.",
            border_style="blue",
        )
    )

    # Get current values
    current_bot_token = os.getenv("SLACK_BOT_TOKEN", "")
    current_team_id = os.getenv("SLACK_TEAM_ID", "")
    current_signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
    current_channel_id = os.getenv("SLACK_CHANNEL_ID", "")

    console.print(f"Current Bot Token: [cyan]{'Set' if current_bot_token else 'Not set'}[/cyan]")
    console.print(f"Current Team ID: [cyan]{current_team_id or 'Not set'}[/cyan]")
    console.print(
        f"Current Signing Secret: [cyan]{'Set' if current_signing_secret else 'Not set'}[/cyan]"
    )
    console.print(f"Current Channel ID: [cyan]{current_channel_id or 'Not set'}[/cyan]")

    console.print(
        "\n[dim]💡 Get these values from your Slack app configuration at: "
        "https://api.slack.com/apps[/dim]"
    )

    # Get new values
    bot_token = Prompt.ask("Slack Bot Token (xoxb-...)", password=True, default="")
    if not bot_token and current_bot_token:
        bot_token = current_bot_token

    team_id = Prompt.ask("Slack Team ID", default=current_team_id or "")

    signing_secret = Prompt.ask("Slack Signing Secret", password=True, default="")
    if not signing_secret and current_signing_secret:
        signing_secret = current_signing_secret

    channel_id = Prompt.ask("Slack Channel ID", default=current_channel_id or "")

    # Update environment
    updates = {}
    if bot_token:
        updates["SLACK_BOT_TOKEN"] = bot_token
    if team_id:
        updates["SLACK_TEAM_ID"] = team_id
    if signing_secret:
        updates["SLACK_SIGNING_SECRET"] = signing_secret
    if channel_id:
        updates["SLACK_CHANNEL_ID"] = channel_id

    if updates:
        _update_env_file(updates)


def _configure_llm_firewall() -> None:
    """Configure LLM Firewall settings."""
    console.print(
        Panel(
            "[bold]LLM Firewall Configuration[/bold]\n\n"
            "Configure the LLM Firewall for content filtering and safety.",
            border_style="blue",
        )
    )

    current_hf_token = os.getenv("HF_TOKEN", "")
    console.print(
        f"Current Hugging Face Token: [cyan]{'Set' if current_hf_token else 'Not set'}[/cyan]"
    )

    console.print(
        "\n[dim]💡 Get your Hugging Face token at: https://huggingface.co/settings/tokens[/dim]"
    )

    hf_token = Prompt.ask("Hugging Face Token", password=True, default="")
    if not hf_token and current_hf_token:
        hf_token = current_hf_token

    if hf_token:
        _update_env_file({"HF_TOKEN": hf_token})
    else:
        console.print("[yellow]⚠️  No token provided. LLM Firewall will not be available.[/yellow]")


def _configure_model_provider() -> None:
    """Configure model provider settings."""
    console.print(
        Panel(
            "[bold]Model Provider Configuration[/bold]\n\n"
            "Configure your AI model provider and specific model selection.",
            border_style="blue",
        )
    )

    current_provider = os.getenv("PROVIDER", "")
    current_model = os.getenv("MODEL", "")

    console.print(f"Current Provider: [cyan]{current_provider or 'Not set'}[/cyan]")
    console.print(f"Current Model: [cyan]{current_model or 'Not set'}[/cyan]")

    # Select provider
    console.print("\nAvailable providers:")
    console.print("  1. Anthropic (Claude)")
    console.print("  2. Google (Gemini)")

    provider_choice = Prompt.ask("Select provider", choices=["1", "2"], default="1")

    if provider_choice == "1":
        provider = "anthropic"
        console.print("\nAvailable Anthropic models:")
        console.print("  1. claude-sonnet-4-20250514 (latest, recommended)")
        console.print("  2. claude-3-5-sonnet-20241022")
        console.print("  3. claude-3-opus-20240229")
        console.print("  4. claude-3-haiku-20240307")

        model_choice = Prompt.ask("Select model", choices=["1", "2", "3", "4"], default="1")

        models = {
            "1": "claude-sonnet-4-20250514",
            "2": "claude-3-5-sonnet-20241022",
            "3": "claude-3-opus-20240229",
            "4": "claude-3-haiku-20240307",
        }
        model = models[model_choice]

        console.print(
            "\n[dim]💡 Get your Anthropic API key at: https://console.anthropic.com/[/dim]"
        )
        api_key = Prompt.ask("Anthropic API Key", password=True, default="")
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")

        updates = {"PROVIDER": provider, "MODEL": model}
        if api_key:
            updates["ANTHROPIC_API_KEY"] = api_key

    else:
        provider = "google"
        console.print("\nAvailable Google models:")
        console.print("  1. gemini-pro")
        console.print("  2. gemini-pro-vision")

        model_choice = Prompt.ask("Select model", choices=["1", "2"], default="1")
        model = "gemini-pro" if model_choice == "1" else "gemini-pro-vision"

        console.print(
            "\n[dim]💡 Get your Google API key at: https://makersuite.google.com/app/apikey[/dim]"
        )
        api_key = Prompt.ask("Google API Key", password=True, default="")
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY", "")

        updates = {"PROVIDER": provider, "MODEL": model}
        if api_key:
            updates["GEMINI_API_KEY"] = api_key

    _update_env_file(updates)
    console.print(f"[green]✅ Selected: {provider} - {model}[/green]")


def _view_current_config() -> None:
    """View current configuration."""
    console.print(
        Panel(
            "[bold]Current Configuration[/bold]",
            border_style="green",
        )
    )

    env_file = Path.cwd() / ".env"
    if not env_file.exists():
        console.print("[yellow]⚠️  No .env file found[/yellow]")
        return

    config_table = Table(show_header=True, header_style="bold cyan")
    config_table.add_column("Setting", style="cyan", width=30)
    config_table.add_column("Value", width=50)

    with open(env_file) as f:
        for raw_line in f:
            line = raw_line.strip()
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                # Mask sensitive values
                if any(sensitive in key.lower() for sensitive in ["token", "key", "secret"]):
                    display_value = "***" if value else "Not set"
                else:
                    display_value = value or "Not set"
                config_table.add_row(key, display_value)

    console.print(config_table)


def _reset_configuration() -> None:
    """Reset all configuration."""
    console.print(
        Panel(
            "[bold red]Reset Configuration[/bold red]\n\n"
            "[yellow]⚠️  This will delete all your configuration settings![/yellow]",
            border_style="red",
        )
    )

    if not Confirm.ask("Are you sure you want to reset all configuration?", default=False):
        console.print("[yellow]Configuration reset cancelled[/yellow]")
        return

    # Remove .env file
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        env_file.unlink()
        console.print(f"[green]✅ Deleted {env_file}[/green]")

    console.print("[green]✅ All configuration has been reset[/green]")
    console.print("[cyan]Restart the CLI to run the setup wizard again[/cyan]")


@click.command()
def config() -> None:
    """Interactive configuration menu for SRE Agent settings.

    Access all configuration options including:
    - AWS Kubernetes cluster settings
    - GitHub integration
    - Slack notifications
    - LLM Firewall
    - Model provider selection
    """
    _print_config_header()

    while True:
        choice = _display_main_menu()

        if choice == "1":
            _configure_aws_cluster()
        elif choice == "2":
            _configure_github()
        elif choice == "3":
            _configure_slack()
        elif choice == "4":
            _configure_llm_firewall()
        elif choice == "5":
            _configure_model_provider()
        elif choice == "6":
            _view_current_config()
        elif choice == "7":
            _reset_configuration()
        elif choice == "8":
            console.print("[cyan]Exiting configuration menu...[/cyan]")
            break

        console.print("\n" + "─" * 80 + "\n")
