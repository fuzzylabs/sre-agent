"""Configuration command for SRE Agent CLI."""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..utils.config import (
    ConfigError,
    SREAgentConfig,
    get_bearer_token_from_env,
    get_config_path,
    load_config,
    save_config,
)
from ..utils.env_setup import EnvSetup
from ..utils.service_manager import ServiceManager
from .platform import PlatformDetector

console = Console()


def _print_setup_header() -> None:
    console.print(
        Panel(
            "[bold cyan]🔧 SRE Agent CLI Setup[/bold cyan]\n\n"
            "Welcome to the SRE Agent CLI setup wizard!\n"
            "I'll help you configure the CLI for your environment.",
            border_style="cyan",
            title="Setup Wizard",
        )
    )


def _check_prerequisites() -> bool:
    # Docker installed and running
    console.print("[cyan]Checking Docker installation and daemon status...[/cyan]")
    if not shutil.which("docker"):
        console.print("[red]❌ Docker is not installed.[/red]")
        console.print("Please install Docker Desktop or Docker Engine before continuing.")
        console.print("Visit: [cyan]https://docs.docker.com/get-docker/[/cyan]")
        return False
    try:
        docker_info = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=5, check=False
        )
        if docker_info.returncode != 0:
            console.print("[red]❌ Docker is installed but not running.[/red]")
            console.print("Please start Docker Desktop (or the Docker daemon) and try again.")
            return False
    except Exception:
        console.print("[red]❌ Docker is installed but not running or not accessible.[/red]")
        console.print("Please start Docker Desktop (or the Docker daemon) and try again.")
        return False
    console.print("[green]✅ Docker is installed and running[/green]")

    # kubectl installed
    console.print("[cyan]Checking kubectl installation...[/cyan]")
    if not shutil.which("kubectl"):
        console.print("[red]❌ kubectl is not installed.[/red]")
        console.print("Please install kubectl before continuing.")
        console.print("See: [cyan]https://kubernetes.io/docs/tasks/tools/[/cyan]")
        return False
    console.print("[green]✅ kubectl is installed[/green]")

    return True


def _load_existing_config_or_new(config_path: Optional[str]) -> SREAgentConfig:
    try:
        existing_config = load_config(config_path)
        console.print("[green]Found existing configuration (updating)...[/green]")
        return existing_config
    except ConfigError:
        console.print(
            "[yellow]No existing configuration found. Creating new configuration.[/yellow]"
        )
        return SREAgentConfig()


def _display_detected_platforms(detected_platforms: list) -> tuple[list, bool]:
    """Display detected platform tools and return cloud platforms and kubectl status."""
    # Display what tools we found (exclude kubectl from this list)
    found_tools = []
    for platform in detected_platforms:
        if platform == "aws":
            found_tools.append("AWS CLI")
        elif platform == "gcp":
            found_tools.append("GCP CLI")
    if found_tools:
        console.print(f"[green]✅ Found: {', '.join(found_tools)}[/green]")

    cloud_platforms = [p for p in detected_platforms if p in ["aws", "gcp"]]
    has_kubectl = "kubernetes" in detected_platforms
    return cloud_platforms, has_kubectl


def _check_platform_configuration_status(
    detector: PlatformDetector, cloud_platforms: list
) -> tuple[list, list, bool]:
    """Check and display cloud platform configuration status."""
    configured_cloud_platforms = []
    unconfigured_cloud_platforms = []

    for platform in cloud_platforms:
        configured = detector.check_platform_configured(platform)
        if configured:
            configured_cloud_platforms.append(platform)
            console.print(f"[green]✅ {platform.upper()} is already configured[/green]")
        else:
            unconfigured_cloud_platforms.append(platform)
            console.print(f"[yellow]⚠️  {platform.upper()} needs configuration[/yellow]")

    # Check kubectl status separately
    kubectl_configured = False
    if "kubernetes" in list(detector.detect_platforms()):
        kubectl_configured = detector.check_platform_configured("kubernetes")
        if kubectl_configured:
            console.print("[green]✅ kubectl context is configured[/green]")
        else:
            console.print("[yellow]⚠️  kubectl has no active context[/yellow]")

    return configured_cloud_platforms, unconfigured_cloud_platforms, kubectl_configured


def _select_cloud_platform(detected_platforms: list) -> Optional[str]:
    """Prompt user to select cloud platform and validate CLI installation."""
    console.print("\n[cyan]Which cloud platform is your Kubernetes cluster running on?[/cyan]")
    console.print("  1. AWS (EKS)")
    console.print("  2. GCP (GKE)")
    choice = Prompt.ask("Choose platform", choices=["1", "2"], default="1")

    if choice == "1":
        platform = "aws"
        if "aws" not in detected_platforms:
            console.print("[red]❌ AWS CLI is not installed. Please install it first:[/red]")
            console.print('   curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"')
            console.print("   sudo installer -pkg AWSCLIV2.pkg -target /")
            return None
    else:
        platform = "gcp"
        if "gcp" not in detected_platforms:
            console.print("[red]❌ GCP CLI is not installed. Please install it first:[/red]")
            console.print("   curl https://sdk.cloud.google.com | bash")
            console.print("   exec -l $SHELL")
            return None

    return platform


def _clear_existing_configuration(platform: str) -> None:
    """Clear existing credentials, kubectl context, and .env file."""
    # Clear existing AWS credentials if applicable
    if platform == "aws":
        import os

        credentials_file = os.path.expanduser("~/.aws/credentials")
        if os.path.exists(credentials_file):
            try:
                os.remove(credentials_file)
                console.print("[dim]Cleared existing AWS credentials file[/dim]")
            except Exception:
                pass

    # Clear kubectl context to force reconfiguration
    try:
        subprocess.run(
            ["kubectl", "config", "unset", "current-context"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        console.print("[dim]Cleared existing kubectl context[/dim]")
    except Exception:
        pass

    # Clear existing .env file to force fresh setup
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        try:
            env_file.unlink()
            console.print("[dim]Cleared existing .env file[/dim]")
        except Exception:
            pass


def _setup_cloud_credentials(detector: PlatformDetector, platform: str) -> Optional[str]:
    """Set up cloud credentials for the selected platform."""
    console.print(f"\nSetting up {platform.upper()} credentials...")

    if platform == "aws" and detector.setup_aws_credentials():
        return "aws"
    elif platform == "gcp" and detector.setup_gcp_credentials():
        return "gcp"
    else:
        console.print(
            (f"[red]❌ {platform.upper()} configuration failed. "),
            ("SRE Agent requires cloud credentials to work.[/red]"),
        )
        console.print("Please try again or check your cloud CLI installation.")
        return None


def _configure_single_cluster(detector: PlatformDetector, cluster: dict) -> bool:
    """Configure kubectl access for a single cluster."""
    console.print(f"[cyan]Configuring access to {cluster['name']}...[/cyan]")
    if detector.configure_kubectl_access(cluster):
        console.print(f"[green]✅ kubectl configured for {cluster['name']}[/green]")
        return True
    else:
        console.print(f"[red]❌ Failed to configure kubectl for {cluster['name']}[/red]")
        console.print("SRE Agent requires kubectl access to work properly.")
        console.print("Please check your cloud credentials and cluster permissions.")
        return False


def _configure_multiple_clusters(detector: PlatformDetector, clusters: list) -> bool:
    """Configure kubectl access for multiple clusters with user choice."""
    console.print("\nAvailable clusters:")
    for i, cluster in enumerate(clusters, 1):
        console.print(f"  {i}. {cluster['name']} ({cluster['type']}) - {cluster['region']}")

    cluster_choices = [str(i) for i in range(1, len(clusters) + 1)] + ["all"]
    choice = Prompt.ask("Configure access to which cluster?", choices=cluster_choices, default="1")

    if choice == "all":
        success_count = 0
        for cluster in clusters:
            if detector.configure_kubectl_access(cluster):
                console.print(f"[green]✅ kubectl configured for {cluster['name']}[/green]")
                success_count += 1
            else:
                console.print(f"[red]❌ Failed to configure kubectl for {cluster['name']}[/red]")

        if success_count == 0:
            console.print("[red]❌ Failed to configure kubectl for any clusters.[/red]")
            console.print("SRE Agent requires kubectl access to work properly.")
            return False
        return True
    else:
        cluster_idx = int(choice) - 1
        cluster = clusters[cluster_idx]
        return _configure_single_cluster(detector, cluster)


def _handle_no_clusters_found(detector: PlatformDetector) -> bool:
    """Handle the case when no Kubernetes clusters are found."""
    console.print("[yellow]No EKS clusters found in the specified region.[/yellow]")
    console.print()
    console.print("[bold]Options:[/bold]")
    console.print("1. Create an EKS cluster in AWS Console")
    console.print("2. Use existing kubectl context (if you have one)")
    console.print("3. Continue without Kubernetes (limited functionality)")
    console.print()

    choice = Prompt.ask("What would you like to do?", choices=["1", "2", "3"], default="3")

    if choice == "1":
        console.print("[cyan]Create an EKS cluster in AWS Console, then run setup again.[/cyan]")
        return False
    elif choice == "2":
        try:
            result = subprocess.run(
                ["kubectl", "config", "get-contexts"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0 and len(result.stdout.strip().split("\n")) > 1:
                console.print("[green]✅ Found existing kubectl contexts. Continuing...[/green]")
                return True
            else:
                console.print("[red]❌ No kubectl contexts found.[/red]")
                console.print("Please set up kubectl access to your clusters first.")
                return False
        except Exception:
            console.print("[red]❌ Could not check kubectl contexts.[/red]")
            return False
    elif choice == "3":
        console.print("[yellow]⚠️  Continuing without Kubernetes cluster access.[/yellow]")
        console.print("[dim]Some SRE Agent features will be limited.[/dim]")
        return True

    return False


def _configure_kubectl_access(
    detector: PlatformDetector, primary_platform: str, has_kubectl: bool, kubectl_configured: bool
) -> bool:
    """Configure kubectl access for the selected platform."""
    if not primary_platform or not has_kubectl or kubectl_configured:
        return True

    console.print(f"\n[cyan]Setting up kubectl access for {primary_platform.upper()}...[/cyan]")
    console.print(
        "[dim]kubectl configuration is required for SRE Agent to access your clusters.[/dim]"
    )

    clusters = detector.get_kubernetes_clusters(primary_platform)
    if clusters:
        console.print(f"[green]Found {len(clusters)} cluster(s)[/green]")

        if len(clusters) == 1:
            return _configure_single_cluster(detector, clusters[0])
        else:
            return _configure_multiple_clusters(detector, clusters)
    else:
        return _handle_no_clusters_found(detector)


def _detect_and_configure_platform() -> Optional[str]:
    """Detect and configure cloud platform and kubectl access."""
    # Step 1: Platform Detection & Quick Setup
    console.print("\n[bold]Step 1: Cloud Platform Detection[/bold]")
    detector = PlatformDetector()
    detected_platforms = detector.detect_platforms()

    if not detected_platforms:
        console.print("[yellow]⚠️  No cloud platform tools detected.[/yellow]")
        console.print("Install: AWS CLI, GCP CLI, or kubectl for full functionality")
        return None

    # Display detected platforms and get status
    cloud_platforms, has_kubectl = _display_detected_platforms(detected_platforms)
    (
        configured_cloud_platforms,
        unconfigured_cloud_platforms,
        kubectl_configured,
    ) = _check_platform_configuration_status(detector, cloud_platforms)

    # Select and validate cloud platform
    platform = _select_cloud_platform(detected_platforms)
    if not platform:
        return None

    # Clear existing configuration
    _clear_existing_configuration(platform)

    # Set up cloud credentials
    primary_platform = _setup_cloud_credentials(detector, platform)
    if not primary_platform:
        return None

    # Configure kubectl access
    if not _configure_kubectl_access(detector, primary_platform, has_kubectl, kubectl_configured):
        return None

    if primary_platform:
        console.print(f"\n[green]🎉 Primary platform: {primary_platform.upper()}[/green]")

    return primary_platform


def _setup_environment_variables(primary_platform: Optional[str], full: bool) -> bool:
    console.print("\n[bold]Step 2: Environment Variables[/bold]")
    if primary_platform:
        env_setup = EnvSetup(primary_platform, minimal=not full)
        all_vars_set = env_setup.display_env_status()
        if not all_vars_set:
            console.print("\n[yellow]⚠️  Some required environment variables are missing.[/yellow]")
            console.print("SRE Agent services need these variables to function properly.")
            if not env_setup.interactive_setup():
                console.print("[red]❌ Environment variable setup failed or was cancelled.[/red]")
                console.print("SRE Agent requires environment variables to work properly.")
                console.print(
                    "You can run setup again later with: [cyan]sre-agent config setup[/cyan]"
                )
                return False
        else:
            console.print("[green]✅ All required environment variables are configured![/green]")
    else:
        console.print(
            "[yellow]⚠️  Skipping environment setup - no cloud platform configured.[/yellow]"
        )
    return True


def _check_service_status() -> bool:
    """Check if SRE Agent services are currently running."""
    try:
        import asyncio

        import httpx

        async def check_services():
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get("http://localhost:8003/health")
                    return response.status_code == 200  # noqa: PLR2004
            except Exception:
                return False

        return asyncio.run(check_services())
    except Exception:
        return False


def _get_platform_and_compose_file(primary_platform: Optional[str], full: bool) -> tuple[str, str]:
    """Determine platform argument and compose file path."""
    platform_arg = (
        "aws" if primary_platform == "aws" else "gcp" if primary_platform == "gcp" else "aws"
    )
    compose_file = (
        f"compose.minimal.{platform_arg}.yaml" if not full else f"compose.{platform_arg}.yaml"
    )
    return platform_arg, compose_file


def _validate_service_prerequisites(manager: ServiceManager, platform_arg: str) -> bool:
    """Validate Docker Compose and compose file availability."""
    if not manager.check_docker_compose():
        console.print("[red]❌ Docker or Docker Compose not found.[/red]")
        console.print("Please install Docker Desktop or Docker Engine with Compose plugin.")
        console.print("Visit: [cyan]https://docs.docker.com/get-docker/[/cyan]")
        console.print(
            f"\nAfter installing Docker, run: "
            f"[cyan]sre-agent start --platform {platform_arg}[/cyan]"
        )

        sys.exit(1)

    if not manager.check_compose_file():
        console.print(f"[red]❌ Compose file not found: {manager.compose_file}[/red]")
        console.print("Make sure you're running from the SRE Agent project directory.")

        sys.exit(1)

    return True


def _start_and_monitor_services(manager: ServiceManager) -> None:
    """Start services and monitor their health status."""
    if manager.start_services(detached=True):
        console.print("[green]✅ Services started![/green]")
        console.print("[cyan]Waiting for services to become ready...[/cyan]")

        import asyncio

        status = asyncio.run(manager.wait_for_services())

        healthy_count = sum(1 for s in status.values() if s)
        total_count = len(status)

        if healthy_count == total_count:
            console.print(f"[green]🎉 All {total_count} services are healthy![/green]")
        else:
            console.print(f"[yellow]⚠️  {healthy_count}/{total_count} services healthy[/yellow]")
            console.print(
                "Some services may still be starting. Check logs with: [cyan]sre-agent logs[/cyan]"
            )
    else:
        console.print("[red]❌ Failed to start services.[/red]")


def _handle_service_startup_failure(platform_arg: str) -> None:
    """Handle service startup failures with helpful error messages."""
    console.print("[red]❌ Failed to start services.[/red]")
    console.print(
        f"You can try manually with: [cyan]sre-agent start --platform {platform_arg}[/cyan]"
    )


def _handle_service_startup_error(e: Exception, platform_arg: str) -> None:
    """Handle exceptions during service startup."""
    console.print(f"[red]❌ Error starting services: {e}[/red]")
    console.print(f"Please run manually: [cyan]sre-agent start --platform {platform_arg}[/cyan]")


def _skip_service_startup(primary_platform: Optional[str]) -> None:
    """Handle user choice to skip service startup."""
    console.print(
        "[yellow]Skipping service startup. You'll need to start them later with:[/yellow]"
    )
    platform_arg = (
        "aws" if primary_platform == "aws" else "gcp" if primary_platform == "gcp" else "aws"
    )
    console.print(f"[cyan]sre-agent start --platform {platform_arg}[/cyan]")


def _start_services_interactively(primary_platform: Optional[str], full: bool) -> None:
    """Start services interactively with user confirmation."""
    if primary_platform:
        env_setup = EnvSetup(primary_platform, minimal=not full)
        if not env_setup.display_env_status():
            console.print(
                "[red]❌ Cannot start services - "
                "environment variables are not properly configured.[/red]"
            )
            console.print("Please complete the environment variable setup first.")
            console.print(
                "Run: [cyan]sre-agent config setup[/cyan] to configure missing variables."
            )
            return

    console.print("\n[cyan]Starting SRE Agent services...[/cyan]")
    console.print("[dim]This may take a few minutes the first time.[/dim]")

    platform_arg, compose_file = _get_platform_and_compose_file(primary_platform, full)
    console.print(f"[dim]Starting SRE Agent services with {compose_file}...[/dim]")

    try:
        manager = ServiceManager(platform_arg)
        manager.compose_file = compose_file
        manager._load_services_from_compose()

        if _validate_service_prerequisites(manager, platform_arg):
            _start_and_monitor_services(manager)

    except Exception as e:
        _handle_service_startup_error(e, platform_arg)


def _check_and_maybe_start_services(primary_platform: Optional[str], full: bool) -> None:
    """Check service status and optionally start services."""
    console.print("\n[bold]Step 3: Service Check[/bold]")

    try:
        services_running = _check_service_status()

        if services_running:
            console.print("[green]✅ SRE Agent services are running![/green]")
        else:
            console.print("[yellow]⚠️  SRE Agent services not detected.[/yellow]")

            if Confirm.ask("Would you like to start the SRE Agent services now?", default=True):
                _start_services_interactively(primary_platform, full)
            else:
                _skip_service_startup(primary_platform)

    except Exception as e:
        console.print(f"[dim]Could not check service status: {e}[/dim]")


def _collect_api_and_preferences(existing_config: SREAgentConfig) -> SREAgentConfig:
    console.print("\n[bold]Step 4: API Configuration[/bold]")

    current_api_url = existing_config.api_url
    console.print(
        "[dim]💡 Just press Enter if you haven't modified the code - "
        "the default URL is correct for local development[/dim]"
    )
    api_url = Prompt.ask("API URL", default=current_api_url, show_default=True)

    current_token = existing_config.bearer_token or "Not set"
    console.print(f"Current bearer token: [dim]{current_token}[/dim]")

    env_token = get_bearer_token_from_env()
    if env_token and not existing_config.bearer_token:
        if Confirm.ask("Found bearer token in environment. Use it?"):
            bearer_token = env_token
        else:
            bearer_token = Prompt.ask("Bearer token", password=True)
    else:
        bearer_token = Prompt.ask(
            "Bearer token (leave empty to keep current)", password=True, default=""
        )
        if not bearer_token and existing_config.bearer_token:
            bearer_token = existing_config.bearer_token

    console.print("\n[bold]Step 4: Default Settings[/bold]")
    default_cluster = "no-loafers-for-you"
    default_namespace = "default"
    default_timeout = 300
    console.print(f"[dim]Using default cluster: {default_cluster}[/dim]")
    console.print(f"[dim]Using default namespace: {default_namespace}[/dim]")
    console.print(f"[dim]Using default timeout: {default_timeout} seconds[/dim]")

    console.print("\n[bold]Step 5: Preferences[/bold]")
    output_format = "rich"
    verbose = False
    monitor_interval = 30
    console.print(f"[dim]Using output format: {output_format}[/dim]")
    console.print(f"[dim]Verbose mode: {'enabled' if verbose else 'disabled'}[/dim]")
    console.print(f"[dim]Monitoring interval: {monitor_interval} seconds[/dim]")

    return SREAgentConfig(
        api_url=api_url,
        bearer_token=bearer_token,
        default_cluster=default_cluster,
        default_namespace=default_namespace,
        default_timeout=int(default_timeout),
        output_format=output_format,
        verbose=verbose,
        monitor_interval=int(monitor_interval),
    )


@click.group()
def config():
    """Manage SRE Agent CLI configuration.

    Configure authentication, default settings, and preferences for the CLI.
    """
    pass


@config.command()
@click.option("--config-path", help="Path to configuration file")
@click.option(
    "--full",
    is_flag=True,
    help="Use full configuration (includes optional integrations)",
)
def setup(config_path: Optional[str], full: bool):
    """Interactive setup wizard for SRE Agent CLI configuration.

    This comprehensive setup wizard will:
    - Detect your cloud platforms (AWS, GCP, kubectl)
    - Configure cloud credentials if needed
    - Set up environment variables (.env file)
    - Start SRE Agent services automatically
    - Configure CLI settings and API access

    By default, uses minimal setup with only essential variables.
    Use --full for complete setup including Slack/GitHub integrations.
    This is the only command you need to run to get started!
    """
    _print_setup_header()

    if not _check_prerequisites():
        return

    # Try to load existing config
    existing_config = _load_existing_config_or_new(config_path)

    primary_platform = _detect_and_configure_platform()
    if primary_platform is None:
        # Ensure variable defined for later use but continue to allow limited setup
        primary_platform = None

    # Step 2: Environment Variables Setup
    if not _setup_environment_variables(primary_platform, full):
        return

    # Step 3: Service Check and Startup
    _check_and_maybe_start_services(primary_platform, full)

    new_config = _collect_api_and_preferences(existing_config)

    # Show configuration summary
    console.print("\n[bold]Configuration Summary:[/bold]")
    _display_config(new_config, mask_token=True)

    if Confirm.ask("\nSave this configuration?"):
        try:
            save_config(new_config, config_path)
            config_file_path = get_config_path(config_path)
            console.print(f"[green]✅ Configuration saved to {config_file_path}[/green]")
            console.print("\n[cyan]You're all set! Try running:[/cyan]")
            console.print("  [dim]sre-agent diagnose --service myapp[/dim]")
            console.print("  [dim]sre-agent interactive[/dim]")
        except ConfigError as e:
            console.print(f"[red]Failed to save configuration: {e}[/red]")
    else:
        console.print("[yellow]Configuration not saved.[/yellow]")


@config.command()
@click.option("--config-path", help="Path to configuration file")
def show(config_path: Optional[str]):
    """Show current configuration.

    Display the current CLI configuration settings.
    """
    try:
        config_data = load_config(config_path)
        config_file_path = get_config_path(config_path)

        console.print(
            Panel(
                f"Configuration loaded from: [cyan]{config_file_path}[/cyan]",
                border_style="cyan",
            )
        )

        _display_config(config_data, mask_token=True)

    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("[yellow]Run 'sre-agent config setup' to configure the CLI[/yellow]")


@config.command()
@click.option("--config-path", help="Path to configuration file")
def validate(config_path: Optional[str]):
    """Validate current configuration.

    Check if the current configuration is valid and can connect to the API.
    """
    try:
        config_data = load_config(config_path)

        # Basic validation
        issues = []

        if not config_data.bearer_token:
            issues.append("Bearer token not configured")

        if not config_data.api_url:
            issues.append("API URL not configured")
        elif not config_data.api_url.startswith(("http://", "https://")):
            issues.append("API URL should start with http:// or https://")

        if config_data.default_timeout <= 0:
            issues.append("Default timeout should be greater than 0")

        if config_data.monitor_interval <= 0:
            issues.append("Monitor interval should be greater than 0")

        if issues:
            console.print(
                Panel(
                    "\n".join([f"❌ {issue}" for issue in issues]),
                    title="[bold red]Configuration Issues[/bold red]",
                    border_style="red",
                )
            )
        else:
            console.print(
                Panel(
                    "✅ Configuration is valid!",
                    title="[bold green]Validation Successful[/bold green]",
                    border_style="green",
                )
            )

            # TODO: Add API connectivity test
            console.print("\n[dim]Note: API connectivity test not yet implemented[/dim]")

    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")


@config.command()
@click.option("--config-path", help="Path to configuration file")
@click.confirmation_option(prompt="Are you sure you want to reset the configuration?")
def reset(config_path: Optional[str]):
    """Reset configuration to defaults.

    This will delete the current configuration file and reset all settings
    to their default values.
    """
    config_file_path = get_config_path(config_path)

    try:
        if config_file_path.exists():
            config_file_path.unlink()
            console.print(f"[green]✅ Configuration file deleted: {config_file_path}[/green]")
        else:
            console.print("[yellow]No configuration file found to delete.[/yellow]")

        console.print("[cyan]Run 'sre-agent config setup' to create a new configuration.[/cyan]")

    except Exception as e:
        console.print(f"[red]Failed to reset configuration: {e}[/red]")


def _display_config(config: SREAgentConfig, mask_token: bool = True):
    """Display configuration in a formatted table."""
    table = Table(show_header=False, box=None, padding=(0, 1))

    table.add_row("[cyan]API URL:[/cyan]", config.api_url)

    if config.bearer_token:
        if mask_token:
            masked_token = (
                config.bearer_token[:8] + "..." + config.bearer_token[-4:]
                if len(config.bearer_token) > 12  # noqa: PLR2004
                else "***"
            )
            table.add_row("[cyan]Bearer Token:[/cyan]", masked_token)
        else:
            table.add_row("[cyan]Bearer Token:[/cyan]", config.bearer_token)
    else:
        table.add_row("[cyan]Bearer Token:[/cyan]", "[red]Not configured[/red]")

    table.add_row("[cyan]Default Cluster:[/cyan]", config.default_cluster or "[dim]Not set[/dim]")
    table.add_row("[cyan]Default Namespace:[/cyan]", config.default_namespace)
    table.add_row("[cyan]Default Timeout:[/cyan]", f"{config.default_timeout}s")
    table.add_row("[cyan]Output Format:[/cyan]", config.output_format)
    table.add_row("[cyan]Verbose Mode:[/cyan]", "✅ Enabled" if config.verbose else "❌ Disabled")
    table.add_row("[cyan]Monitor Interval:[/cyan]", f"{config.monitor_interval}s")

    console.print(
        Panel(
            table,
            title="[bold cyan]Current Configuration[/bold cyan]",
            border_style="cyan",
        )
    )
