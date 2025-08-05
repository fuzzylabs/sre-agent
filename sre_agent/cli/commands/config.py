"""Configuration command for SRE Agent CLI."""

import os
import subprocess
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text

from ..utils.config import (
    SREAgentConfig, 
    load_config, 
    save_config, 
    get_config_path,
    get_bearer_token_from_env,
    ConfigError
)
from ..utils.env_setup import EnvSetup
from .platform import PlatformDetector

console = Console()


@click.group()
def config():
    """
    Manage SRE Agent CLI configuration.
    
    Configure authentication, default settings, and preferences for the CLI.
    """
    pass


@config.command()
@click.option('--config-path', help='Path to configuration file')
@click.option('--full', is_flag=True, help='Use full configuration (includes optional integrations)')
def setup(config_path: Optional[str], full: bool):
    """
    Interactive setup wizard for SRE Agent CLI configuration.
    
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
    console.print(Panel(
        "[bold cyan]🔧 SRE Agent CLI Setup[/bold cyan]\n\n"
        "Welcome to the SRE Agent CLI setup wizard!\n"
        "I'll help you configure the CLI for your environment.",
        border_style="cyan",
        title="Setup Wizard"
    ))
    
    # Try to load existing config
    try:
        existing_config = load_config(config_path)
        console.print("[green]Found existing configuration![/green]")
        if not Confirm.ask("Would you like to update the existing configuration?"):
            console.print("[yellow]Setup cancelled.[/yellow]")
            return
    except ConfigError:
        existing_config = SREAgentConfig()
        console.print("[yellow]No existing configuration found. Creating new configuration.[/yellow]")
    
    # Step 0: Platform Detection & Quick Setup
    console.print("\n[bold]Step 1: Cloud Platform Detection[/bold]")
    detector = PlatformDetector()
    detected_platforms = detector.detect_platforms()
    
    if detected_platforms:
        # Create more descriptive names for what we found
        found_tools = []
        for platform in detected_platforms:
            if platform == 'aws':
                found_tools.append('AWS CLI')
            elif platform == 'gcp':
                found_tools.append('GCP CLI')
            elif platform == 'kubernetes':
                found_tools.append('kubectl')
        
        console.print(f"[green]✅ Found: {', '.join(found_tools)}[/green]")
        
        # Separate cloud platforms from kubernetes
        cloud_platforms = [p for p in detected_platforms if p in ['aws', 'gcp']]
        has_kubectl = 'kubernetes' in detected_platforms
        
        # Check cloud platform configuration status
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
        if has_kubectl:
            kubectl_configured = detector.check_platform_configured('kubernetes')
            if kubectl_configured:
                console.print("[green]✅ kubectl context is configured[/green]")
            else:
                console.print("[yellow]⚠️  kubectl has no active context[/yellow]")
        
        primary_platform = None
        
        # Step 1: Configure cloud platform first
        if configured_cloud_platforms:
            # Use already configured cloud platform
            primary_platform = configured_cloud_platforms[0]
            console.print(f"[green]✅ Using {primary_platform.upper()} as primary cloud platform[/green]")
        elif unconfigured_cloud_platforms:
            # Need to configure a cloud platform
            if len(unconfigured_cloud_platforms) == 1:
                # Only one cloud platform available
                platform = unconfigured_cloud_platforms[0]
                if Confirm.ask(f"Configure {platform.upper()} credentials now?", default=True):
                    if platform == 'aws' and detector.setup_aws_credentials():
                        primary_platform = 'aws'
                    elif platform == 'gcp' and detector.setup_gcp_credentials():
                        primary_platform = 'gcp'
                    else:
                        console.print(f"[red]❌ {platform.upper()} configuration failed. SRE Agent requires cloud credentials to work.[/red]")
                        console.print("Please try again or check your cloud CLI installation.")
                        return
                else:
                    console.print(f"[red]❌ {platform.upper()} credentials are required for SRE Agent to work.[/red]")
                    console.print("Run 'sre-agent config setup' again when ready to configure credentials.")
                    return
            else:
                # Multiple cloud platforms - let user choose
                console.print(f"\n[cyan]Multiple cloud platforms available: {', '.join(p.upper() for p in unconfigured_cloud_platforms)}[/cyan]")
                
                # Create choices for cloud platforms only
                choices = []
                choice_map = {}
                for i, platform in enumerate(unconfigured_cloud_platforms, 1):
                    choices.append(str(i))
                    choice_map[str(i)] = platform
                choices.append('skip')
                
                # Show cloud platform options (no skip option - credentials are required)
                console.print("\nWhich cloud platform would you like to configure?")
                for i, platform in enumerate(unconfigured_cloud_platforms, 1):
                    console.print(f"  {i}. {platform.upper()}")
                
                # Remove skip from choices - cloud credentials are required
                choice = Prompt.ask("Choose cloud platform", choices=choices[:-1], default="1")
                
                platform = choice_map[choice]
                console.print(f"\n[cyan]Configuring {platform.upper()}...[/cyan]")
                
                if platform == 'aws' and detector.setup_aws_credentials():
                    primary_platform = 'aws'
                elif platform == 'gcp' and detector.setup_gcp_credentials():
                    primary_platform = 'gcp'
                else:
                    console.print(f"[red]❌ {platform.upper()} configuration failed. SRE Agent requires cloud credentials to work.[/red]")
                    console.print("Please try again or check your cloud CLI installation.")
                    return
        
        # Step 2: Configure kubectl access after cloud platform is set up (required)
        if primary_platform and has_kubectl and not kubectl_configured:
            console.print(f"\n[cyan]Setting up kubectl access for {primary_platform.upper()}...[/cyan]")
            console.print("[dim]kubectl configuration is required for SRE Agent to access your clusters.[/dim]")
            
            # Get clusters for the configured platform
            clusters = detector.get_kubernetes_clusters(primary_platform)
            
            if clusters:
                console.print(f"[green]Found {len(clusters)} cluster(s)[/green]")
                
                # Show available clusters
                if len(clusters) == 1:
                    cluster = clusters[0]
                    console.print(f"[cyan]Configuring access to {cluster['name']}...[/cyan]")
                    if detector.configure_kubectl_access(cluster):
                        console.print(f"[green]✅ kubectl configured for {cluster['name']}[/green]")
                    else:
                        console.print(f"[red]❌ Failed to configure kubectl for {cluster['name']}[/red]")
                        console.print("SRE Agent requires kubectl access to work properly.")
                        console.print("Please check your cloud credentials and cluster permissions.")
                        return
                else:
                    console.print("\nAvailable clusters:")
                    for i, cluster in enumerate(clusters, 1):
                        console.print(f"  {i}. {cluster['name']} ({cluster['type']}) - {cluster['region']}")
                    
                    cluster_choices = [str(i) for i in range(1, len(clusters) + 1)] + ['all']
                    choice = Prompt.ask("Configure access to which cluster?", 
                                      choices=cluster_choices, default="1")
                    
                    if choice == 'all':
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
                            return
                    else:
                        cluster_idx = int(choice) - 1
                        cluster = clusters[cluster_idx]
                        console.print(f"[cyan]Configuring access to {cluster['name']}...[/cyan]")
                        if detector.configure_kubectl_access(cluster):
                            console.print(f"[green]✅ kubectl configured for {cluster['name']}[/green]")
                        else:
                            console.print(f"[red]❌ Failed to configure kubectl for {cluster['name']}[/red]")
                            console.print("SRE Agent requires kubectl access to work properly.")
                            return
            else:
                console.print(f"[yellow]No EKS clusters found in the specified region.[/yellow]")
                console.print()
                console.print("[bold]Options:[/bold]")
                console.print("1. Create an EKS cluster in AWS Console")
                console.print("2. Use existing kubectl context (if you have one)")
                console.print("3. Continue without Kubernetes (limited functionality)")
                console.print()
                
                choice = Prompt.ask("What would you like to do?", 
                                  choices=["1", "2", "3"], default="3")
                
                if choice == "1":
                    console.print("[cyan]Create an EKS cluster in AWS Console, then run setup again.[/cyan]")
                    return
                elif choice == "2":
                    # Check if kubectl has any contexts
                    try:
                        result = subprocess.run(['kubectl', 'config', 'get-contexts'], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0 and len(result.stdout.strip().split('\n')) > 1:
                            console.print("[green]✅ Found existing kubectl contexts. Continuing...[/green]")
                        else:
                            console.print("[red]❌ No kubectl contexts found.[/red]")
                            console.print("Please set up kubectl access to your clusters first.")
                            return
                    except Exception:
                        console.print("[red]❌ Could not check kubectl contexts.[/red]")
                        return
                elif choice == "3":
                    console.print("[yellow]⚠️  Continuing without Kubernetes cluster access.[/yellow]")
                    console.print("[dim]Some SRE Agent features will be limited.[/dim]")
        
        if primary_platform:
            console.print(f"\n[green]🎉 Primary platform: {primary_platform.upper()}[/green]")
    else:
        console.print("[yellow]⚠️  No cloud platform tools detected.[/yellow]")
        console.print("Install: AWS CLI, GCP CLI, or kubectl for full functionality")
        primary_platform = None  # Ensure variable is defined for later use
    
    # Step 2: Environment Variables Setup
    console.print("\n[bold]Step 2: Environment Variables[/bold]")
    if primary_platform:
        env_setup = EnvSetup(primary_platform, minimal=not full)
        
        # Check current status
        all_vars_set = env_setup.display_env_status()
        
        if not all_vars_set:
            console.print("\n[yellow]⚠️  Some required environment variables are missing.[/yellow]")
            console.print("SRE Agent services need these variables to function properly.")
            
            if not env_setup.interactive_setup():
                console.print("[red]❌ Environment variable setup failed or was cancelled.[/red]")
                console.print("SRE Agent requires environment variables to work properly.")
                console.print(f"You can run setup again later with: [cyan]sre-agent config setup[/cyan]")
                return
        else:
            console.print("[green]✅ All required environment variables are configured![/green]")
    else:
        console.print("[yellow]⚠️  Skipping environment setup - no cloud platform configured.[/yellow]")
    
    # Step 3: Service Check and Startup
    console.print("\n[bold]Step 3: Service Check[/bold]")
    try:
        import httpx
        import asyncio
        async def check_services():
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get("http://localhost:8003/health")
                    return response.status_code == 200
            except:
                return False
        
        services_running = asyncio.run(check_services())
        if services_running:
            console.print("[green]✅ SRE Agent services are running![/green]")
        else:
            console.print("[yellow]⚠️  SRE Agent services not detected.[/yellow]")
            
            if Confirm.ask("Would you like to start the SRE Agent services now?", default=True):
                console.print("\n[cyan]Starting SRE Agent services...[/cyan]")
                console.print("[dim]This may take a few minutes the first time.[/dim]")
                
                # Determine platform for startup command
                platform_arg = 'aws' if primary_platform == 'aws' else 'gcp' if primary_platform == 'gcp' else 'aws'
                
                # Import and use the startup functionality
                try:
                    from .startup import ServiceManager
                    import asyncio
                    
                    manager = ServiceManager(platform_arg)
                    
                    # Check prerequisites first
                    if not manager.check_docker_compose():
                        console.print("[red]❌ Docker or Docker Compose not found.[/red]")
                        console.print("Please install Docker Desktop or Docker Engine with Compose plugin.")
                        console.print("Visit: [cyan]https://docs.docker.com/get-docker/[/cyan]")
                        console.print(f"\nAfter installing Docker, run: [cyan]sre-agent startup start --platform {platform_arg}[/cyan]")
                        return
                    
                    if not manager.check_compose_file():
                        console.print(f"[red]❌ Compose file not found: {manager.compose_file}[/red]")
                        console.print("Make sure you're running from the SRE Agent project directory.")
                        return
                    
                    # Start services
                    if manager.start_services(detached=True):
                        console.print("[green]✅ Services started![/green]")
                        
                        # Wait for services to be healthy
                        console.print("[cyan]Waiting for services to become ready...[/cyan]")
                        status = asyncio.run(manager.wait_for_services())
                        
                        healthy_count = sum(1 for s in status.values() if s)
                        total_count = len(status)
                        
                        if healthy_count == total_count:
                            console.print(f"[green]🎉 All {total_count} services are healthy![/green]")
                        else:
                            console.print(f"[yellow]⚠️  {healthy_count}/{total_count} services healthy[/yellow]")
                            console.print("Some services may still be starting. Check logs with: [cyan]sre-agent startup logs[/cyan]")
                    else:
                        console.print("[red]❌ Failed to start services.[/red]")
                        console.print(f"You can try manually with: [cyan]sre-agent startup start --platform {platform_arg}[/cyan]")
                        
                except Exception as e:
                    console.print(f"[red]❌ Error starting services: {e}[/red]")
                    console.print(f"Please run manually: [cyan]sre-agent startup start --platform {platform_arg}[/cyan]")
            else:
                console.print("[yellow]Skipping service startup. You'll need to start them later with:[/yellow]")
                platform_arg = 'aws' if primary_platform == 'aws' else 'gcp' if primary_platform == 'gcp' else 'aws'
                console.print(f"[cyan]sre-agent startup start --platform {platform_arg}[/cyan]")
                
    except Exception as e:
        console.print(f"[dim]Could not check service status: {e}[/dim]")
    
    console.print("\n[bold]Step 4: API Configuration[/bold]")
    
    # API URL
    current_api_url = existing_config.api_url
    api_url = Prompt.ask(
        "API URL",
        default=current_api_url,
        show_default=True
    )
    
    # Bearer Token
    current_token = existing_config.bearer_token or "Not set"
    console.print(f"Current bearer token: [dim]{current_token}[/dim]")
    
    # Try to auto-detect token from environment
    env_token = get_bearer_token_from_env()
    if env_token and not existing_config.bearer_token:
        if Confirm.ask(f"Found bearer token in environment. Use it?"):
            bearer_token = env_token
        else:
            bearer_token = Prompt.ask("Bearer token", password=True)
    else:
        bearer_token = Prompt.ask(
            "Bearer token (leave empty to keep current)", 
            password=True,
            default=""
        )
        if not bearer_token and existing_config.bearer_token:
            bearer_token = existing_config.bearer_token
    
    console.print("\n[bold]Step 4: Default Settings[/bold]")
    
    # Default cluster
    default_cluster = Prompt.ask(
        "Default Kubernetes cluster",
        default=existing_config.default_cluster or "",
        show_default=True
    )
    if not default_cluster:
        default_cluster = None
    
    # Default namespace
    default_namespace = Prompt.ask(
        "Default Kubernetes namespace",
        default=existing_config.default_namespace,
        show_default=True
    )
    
    # Timeout
    default_timeout = Prompt.ask(
        "Default request timeout (seconds)",
        default=str(existing_config.default_timeout),
        show_default=True
    )
    
    console.print("\n[bold]Step 5: Preferences[/bold]")
    
    # Output format
    output_format = click.prompt(
        "Output format",
        type=click.Choice(['rich', 'json', 'plain']),
        default=existing_config.output_format,
        show_default=True
    )
    
    # Verbose mode
    verbose = Confirm.ask(
        "Enable verbose output by default?",
        default=existing_config.verbose
    )
    
    # Monitor interval
    monitor_interval = Prompt.ask(
        "Default monitoring interval (seconds)",
        default=str(existing_config.monitor_interval),
        show_default=True
    )
    
    # Create new configuration
    new_config = SREAgentConfig(
        api_url=api_url,
        bearer_token=bearer_token,
        default_cluster=default_cluster,
        default_namespace=default_namespace,
        default_timeout=int(default_timeout),
        output_format=output_format,
        verbose=verbose,
        monitor_interval=int(monitor_interval)
    )
    
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
@click.option('--config-path', help='Path to configuration file')
def show(config_path: Optional[str]):
    """
    Show current configuration.
    
    Display the current CLI configuration settings.
    """
    try:
        config_data = load_config(config_path)
        config_file_path = get_config_path(config_path)
        
        console.print(Panel(
            f"Configuration loaded from: [cyan]{config_file_path}[/cyan]",
            border_style="cyan"
        ))
        
        _display_config(config_data, mask_token=True)
        
    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("[yellow]Run 'sre-agent config setup' to configure the CLI[/yellow]")


@config.command()
@click.option('--config-path', help='Path to configuration file')
def validate(config_path: Optional[str]):
    """
    Validate current configuration.
    
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
        elif not config_data.api_url.startswith(('http://', 'https://')):
            issues.append("API URL should start with http:// or https://")
        
        if config_data.default_timeout <= 0:
            issues.append("Default timeout should be greater than 0")
        
        if config_data.monitor_interval <= 0:
            issues.append("Monitor interval should be greater than 0")
        
        if issues:
            console.print(Panel(
                "\n".join([f"❌ {issue}" for issue in issues]),
                title="[bold red]Configuration Issues[/bold red]",
                border_style="red"
            ))
        else:
            console.print(Panel(
                "✅ Configuration is valid!",
                title="[bold green]Validation Successful[/bold green]",
                border_style="green"
            ))
            
            # TODO: Add API connectivity test
            console.print("\n[dim]Note: API connectivity test not yet implemented[/dim]")
        
    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")


@config.command()
@click.option('--config-path', help='Path to configuration file')
@click.confirmation_option(prompt='Are you sure you want to reset the configuration?')
def reset(config_path: Optional[str]):
    """
    Reset configuration to defaults.
    
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
            masked_token = config.bearer_token[:8] + "..." + config.bearer_token[-4:] if len(config.bearer_token) > 12 else "***"
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
    
    console.print(Panel(
        table,
        title="[bold cyan]Current Configuration[/bold cyan]",
        border_style="cyan"
    ))