"""Interactive shell for SRE Agent CLI.

Provides a persistent interactive shell experience where users can run
multiple commands within the SRE Agent context.
"""

import asyncio
import cmd
import os
import shlex
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import httpx

import questionary
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from questionary import Style as QuestionaryStyle
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .commands.config import (
    _configure_aws_cluster,
    _configure_github,
    _configure_llm_firewall,
    _configure_model_provider,
    _configure_slack,
    _display_main_menu,
    _normalise_choice,
    _reset_configuration,
    _update_env_file,
    _view_current_config,
)
from .commands.diagnose import _run_diagnosis
from .utils.config import ConfigError, SREAgentConfig, get_bearer_token_from_env, load_config
from .utils.paths import get_compose_file_path, get_env_file_path

# HTTP status codes
HTTP_OK = 200
HTTP_UNAUTHORISED = 401
HTTP_NOT_FOUND = 404

# Service management constants
MIN_RUNNING_SERVICES = 3  # Minimum number of services to consider the system "running"

console = Console()

# Custom questionary style matching Rich's cyan/blue theme
sre_agent_style = QuestionaryStyle(
    [
        ("qmark", "fg:cyan bold"),  # Question mark
        ("question", "bold"),  # Question text
        ("answer", "fg:cyan bold"),  # Selected answer
        ("pointer", "fg:cyan bold"),  # Selection pointer
        ("highlighted", "fg:cyan bold"),  # Highlighted choice
        ("selected", "fg:cyan"),  # Selected choice
        ("separator", "fg:#cc5454"),  # Separators
        ("instruction", ""),  # User instructions
        ("text", ""),  # Plain text
    ]
)


class SREAgentShell(cmd.Cmd):
    """Interactive shell for SRE Agent commands."""

    intro = None  # We'll show our custom intro
    prompt = ""  # We'll use rich formatting for the prompt

    def __init__(self, dev_mode: bool = False) -> None:
        """Initialize the SRE Agent interactive shell."""
        super().__init__()
        self.config: Optional[SREAgentConfig] = None
        self.current_cluster = "Not set"
        self.current_namespace = "default"
        self.current_context = "Not connected"
        self.is_first_run = False
        self.dev_mode = dev_mode

        # Initialise prompt session with persistent history
        history_file = Path.home() / ".sre_agent_history"
        self.prompt_session: PromptSession[str] = PromptSession(
            history=FileHistory(str(history_file))
        )

        self._load_config()
        self._update_status()

        # Auto-start services if configured but not running
        if not self.is_first_run and self.config:
            self._auto_start_services_if_needed()

    def _load_config(self) -> None:
        """Load configuration if available."""
        # Check if this is first run
        env_file = get_env_file_path()
        self.is_first_run = not env_file.exists()

        # Load environment variables from .env file
        if env_file.exists():
            # Reload environment variables
            from dotenv import load_dotenv

            load_dotenv(env_file, override=True)

        try:
            self.config = load_config(None)
            # Extract cluster info from environment
            self.current_cluster = os.getenv("TARGET_EKS_CLUSTER_NAME", "Not set")
            self.current_namespace = "default"  # Could be made configurable
            if self.current_cluster != "Not set":
                self.current_context = f"{self.current_cluster} ({self.current_namespace})"
            else:
                self.current_context = "Not configured"
        except ConfigError:
            self.config = None

    def _update_status(self) -> None:
        """Update the status display."""
        # This will be called to refresh the status bar
        pass

    def _get_enabled_profiles(self) -> list[str]:
        """Determine which Docker Compose profiles to enable based on PROFILES env var.

        Returns:
            List of profile names to enable (e.g., ['slack', 'firewall'])
        """
        profiles_str = os.getenv("PROFILES", "")

        if not profiles_str or profiles_str.strip() == "":
            return []

        # Parse comma-separated list
        profiles = [p.strip() for p in profiles_str.split(",") if p.strip()]
        return profiles

    def _auto_start_services_if_needed(self) -> None:
        """Auto-start services if they're configured but not running.

        Automatically detects and enables optional service profiles based on configuration.
        """
        try:
            # Check if services are already running
            if self._are_services_running():
                return  # Services already running, nothing to do

            # Reload environment to ensure profile detection works
            from dotenv import load_dotenv

            env_file = get_env_file_path()
            if env_file.exists():
                load_dotenv(env_file, override=True)

            console.print("[cyan]Starting SRE Agent services...[/cyan]")

            # Start services (with automatic profile detection)
            if self._start_docker_services():
                console.print("[green]✅ Services started successfully![/green]")
            else:
                console.print("[yellow]⚠️  Failed to start services automatically[/yellow]")
                console.print("[dim]You can try running 'config' to check your setup[/dim]")

        except Exception:
            # Don't disrupt startup if auto-start fails
            console.print("[yellow]⚠️  Could not auto-start services[/yellow]")
            console.print("[dim]You can start them manually with 'config'[/dim]")

    def _are_services_running(self) -> bool:
        """Check if SRE Agent services are currently running."""
        try:
            result = subprocess.run(  # nosec B603 B607
                ["docker", "ps", "--filter", "name=sre-agent-", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0:
                running_services = [
                    line.strip() for line in result.stdout.strip().split("\n") if line.strip()
                ]
                # Consider services running if we have at least the minimum core services
                return len(running_services) >= MIN_RUNNING_SERVICES

            return False

        except Exception:
            return False

    def _restart_services_with_profiles(self) -> bool:
        """Restart Docker Compose services with updated profiles.

        Returns:
            True if restart succeeded, False otherwise
        """
        compose_file_path = get_compose_file_path(self.dev_mode)
        env_file_path = get_env_file_path()

        try:
            # Step 1: Stop current services
            # Use ALL possible profiles to ensure profiled services are stopped
            # This is necessary because we don't know which profiles were enabled before
            console.print("[cyan]Stopping services...[/cyan]")

            stop_cmd = ["docker", "compose", "-f", str(compose_file_path)]

            # Add env file if it exists
            if env_file_path.exists():
                stop_cmd.extend(["--env-file", str(env_file_path)])

            # Add ALL possible profiles to ensure everything is stopped
            stop_cmd.extend(["--profile", "slack", "--profile", "firewall", "down"])

            stop_result = subprocess.run(  # nosec B603 B607
                stop_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if stop_result.returncode != 0:
                console.print(f"[yellow]⚠️  Warning during shutdown: {stop_result.stderr}[/yellow]")

            # Step 2: Start with new profiles
            console.print("[cyan]Starting services with updated configuration...[/cyan]")
            return self._start_docker_services()

        except subprocess.TimeoutExpired:
            console.print("[red]❌ Service shutdown timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Failed to restart services: {e}[/red]")
            return False

    def _run_first_time_setup(self) -> bool:
        """Run first-time setup for essential credentials.

        Returns True if setup completed successfully, False if cancelled.
        """
        console.print(
            Panel(
                "[bold cyan]🚀 Let's configure your SRE Agent![/bold cyan]\n\n"
                "To start diagnosing services in your cluster, we need to set up:\n"
                "• [cyan]AWS credentials[/cyan] - Access to your Kubernetes cluster\n"
                "• [cyan]GitHub credentials[/cyan] - Access to your application code\n"
                "• [cyan]Anthropic API key[/cyan] - AI model for diagnostics",
                border_style="cyan",
                title="First-Time Setup",
                title_align="center",
            )
        )

        console.print("\n[bright_yellow]Step 1: AWS Authentication & Cluster Setup[/bright_yellow]")
        console.print("[dim]This allows SRE Agent to connect to your EKS cluster[/dim]")

        configure_aws = questionary.confirm(
            "Configure AWS access now?", default=True, style=sre_agent_style
        ).ask()
        if configure_aws is None or not configure_aws:
            console.print(
                "[yellow]Skipping AWS configuration. "
                "You can configure it later with 'config'.[/yellow]"
            )
        else:
            # This will exit if configuration fails
            self._configure_aws_credentials_and_cluster()

        console.print("\n[bright_yellow]Step 2: GitHub Integration[/bright_yellow]")
        console.print(
            "[dim]This allows SRE Agent to access your application code and create issues[/dim]"
        )

        configure_github = questionary.confirm(
            "Configure GitHub integration now?", default=True, style=sre_agent_style
        ).ask()
        if configure_github is None or not configure_github:
            console.print(
                "[yellow]Skipping GitHub configuration. "
                "You can configure it later with 'config'.[/yellow]"
            )
        else:
            self._configure_github_simple()

        console.print("\n[bright_yellow]Step 3: AI Model Provider (Anthropic)[/bright_yellow]")
        console.print("[dim]This provides the AI capabilities for service diagnosis[/dim]")

        configure_anthropic = questionary.confirm(
            "Configure Anthropic API key now?", default=True, style=sre_agent_style
        ).ask()
        if configure_anthropic is None or not configure_anthropic:
            console.print(
                "[yellow]Skipping Anthropic configuration. "
                "You can configure it later with 'config'.[/yellow]"
            )
        else:
            self._configure_anthropic_simple()

        # Check if any configuration was set up
        env_file = get_env_file_path()
        if env_file.exists():
            console.print(
                Panel(
                    "[green]✅ Setup completed![/green]\n\nStarting SRE Agent services...",
                    border_style="green",
                    title="🎉 Configuration Complete!",
                    title_align="center",
                )
            )

            # Start Docker Compose services
            if self._start_docker_services():
                console.print(
                    Panel(
                        "[green]🚀 SRE Agent is now running![/green]\n\n"
                        "You can now:\n"
                        "• Use [cyan]diagnose [service][/cyan] to start diagnosing services\n"
                        "• Use [cyan]config[/cyan] to modify settings or add Slack/LLM Firewall\n"
                        "• Use [cyan]help[/cyan] to see all available commands",
                        border_style="green",
                        title="🎉 Ready to Go!",
                        title_align="center",
                    )
                )
            else:
                console.print(
                    Panel(
                        "[red]❌ Services failed to start.[/red]\n\n"
                        "Docker Compose startup failed. This means the setup is incomplete.",
                        border_style="red",
                        title="Setup Failed",
                    )
                )
                self._cleanup_incomplete_setup()
                console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
                sys.exit(1)

            # Reload config after setup
            self._load_config()
            return True
        else:
            console.print(
                Panel(
                    "[yellow]⚠️  No configuration was set up.[/yellow]\n\n"
                    "You can run the setup again anytime with the [cyan]config[/cyan] command.",
                    border_style="yellow",
                    title="Setup Incomplete",
                )
            )
            return False

    def _configure_anthropic_simple(self) -> None:
        """Simple Anthropic configuration for first-time setup."""
        from rich.prompt import Prompt

        console.print(
            "\n[dim]💡 Get your Anthropic API key at: https://console.anthropic.com/[/dim]"
        )

        api_key = Prompt.ask("Anthropic API Key", password=True, default="")

        if api_key:
            # Test Anthropic API key
            console.print("[cyan]Testing Anthropic API key...[/cyan]")
            if self._test_anthropic_key(api_key):
                updates = {
                    "PROVIDER": "anthropic",
                    "MODEL": "claude-sonnet-4-20250514",
                    "ANTHROPIC_API_KEY": api_key,
                    # Ensure Slack defaults are set if not already configured
                    "SLACK_SIGNING_SECRET": os.getenv("SLACK_SIGNING_SECRET", "null"),
                    "SLACK_CHANNEL_ID": os.getenv("SLACK_CHANNEL_ID", "null"),
                    # Initialize PROFILES if not already set
                    "PROFILES": os.getenv("PROFILES", ""),
                }
                _update_env_file(updates)
                console.print("[green]✅ Anthropic configuration saved[/green]")
                console.print("[green]✅ Using Claude 4 Sonnet [/green]")
            else:
                console.print("[red]❌ Anthropic API key validation failed[/red]")
                console.print("[red]❌ Anthropic configuration failed[/red]")
                self._cleanup_incomplete_setup()
                console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
                sys.exit(1)
        else:
            console.print(
                "[yellow]⚠️  No API key provided. Skipping Anthropic configuration.[/yellow]"
            )

    def _test_github_token(self, token: str, org: str, repo: str) -> bool:
        """Test GitHub PAT token by accessing the repository."""
        try:
            import httpx

            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }

            # Test basic authentication
            with httpx.Client(timeout=10) as client:
                response = client.get("https://api.github.com/user", headers=headers)
                if response.status_code != HTTP_OK:
                    console.print(
                        f"[red]❌ GitHub authentication failed: {response.status_code}[/red]"
                    )
                    return False

                user_data = response.json()
                console.print(
                    f"[green]✅ Authenticated as: {user_data.get('login', 'Unknown')}[/green]"
                )

                # Test repository access
                repo_response = client.get(
                    f"https://api.github.com/repos/{org}/{repo}", headers=headers
                )
                if repo_response.status_code != HTTP_OK:
                    console.print(
                        f"[red]❌ Cannot access repository {org}/{repo}: "
                        f"{repo_response.status_code}[/red]"
                    )
                    if repo_response.status_code == HTTP_NOT_FOUND:
                        console.print("[red]Repository not found or no access[/red]")
                    return False

                console.print(f"[green]✅ Repository {org}/{repo} is accessible[/green]")
                return True

        except Exception as e:
            console.print(f"[red]❌ GitHub token test failed: {e}[/red]")
            return False

    def _handle_anthropic_response(self, response: "httpx.Response") -> bool:
        """Handle Anthropic API response and return validation result."""
        if response.status_code == HTTP_OK:
            console.print("[green]✅ Anthropic API key is valid[/green]")
            return True
        elif response.status_code == HTTP_UNAUTHORISED:
            console.print("[red]❌ Invalid Anthropic API key[/red]")
        else:
            console.print(f"[red]❌ Anthropic API test failed: {response.status_code}[/red]")
        return False

    def _test_anthropic_key(self, api_key: str) -> bool:
        """Test Anthropic API key by making a simple API call."""
        try:
            import httpx

            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            # Simple test with minimal token usage
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hi"}],
            }

            with httpx.Client(timeout=15) as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages", headers=headers, json=payload
                )
                return self._handle_anthropic_response(response)

        except Exception as e:
            console.print(f"[red]❌ Anthropic API key test failed: {e}[/red]")
            return False

    def _get_default_services(self) -> str:
        """Return the default service list as JSON string."""
        return '["cartservice", "adservice", "emailservice", "frontend", "checkoutservice"]'

    def _get_services_from_kubectl(self) -> Optional[list[str]]:
        """Get services from kubectl. Returns None if failed."""
        try:
            kubectl_result = subprocess.run(  # nosec B603 B607
                [
                    "kubectl",
                    "get",
                    "services",
                    "-o",
                    "jsonpath={.items[*].metadata.name}",
                    "--namespace=default",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            if kubectl_result.returncode != 0:
                console.print(
                    f"[yellow]⚠️  Could not discover services: {kubectl_result.stderr}[/yellow]"
                )
                return None

            service_names = kubectl_result.stdout.strip().split()
            if not service_names:
                console.print("[yellow]⚠️  No services found in default namespace[/yellow]")
                return None

            # Filter out system services
            filtered_services = [
                svc
                for svc in service_names
                if not svc.startswith(("kube-", "kubernetes")) and svc != "default"
            ]

            if not filtered_services:
                console.print("[yellow]⚠️  No application services found[/yellow]")
                return None

            return filtered_services

        except Exception as e:
            console.print(f"[yellow]⚠️  Service discovery failed: {e}[/yellow]")
            return None

    def _select_services_from_list(self, services: list[str]) -> str:
        """Let user select services from a list. Returns JSON string."""
        import json

        console.print(f"[green]✅ Found {len(services)} services in the cluster[/green]")

        # Create choices with "All services" option first
        choices = ["All services (recommended)"] + services

        choice = questionary.select(
            "\nSelect services to monitor:",
            choices=choices,
            style=sre_agent_style,
        ).ask()

        # Handle Ctrl+C
        if choice is None:
            console.print("[yellow]Service selection cancelled, using all services[/yellow]")
            return json.dumps(services)

        # Return appropriate JSON
        if choice == "All services (recommended)":
            return json.dumps(services)
        else:
            return json.dumps([choice])

    def _discover_and_select_services(self) -> Optional[str]:
        """Discover services in the cluster and let user select which to monitor."""
        console.print("\n[cyan]Discovering services in your cluster...[/cyan]")

        services = self._get_services_from_kubectl()
        if services:
            return self._select_services_from_list(services)
        else:
            console.print("[dim]Using default service list[/dim]")
            return self._get_default_services()

    def _cleanup_incomplete_setup(self) -> None:
        """Clean up incomplete setup by removing .env file."""
        env_file = get_env_file_path()
        if env_file.exists():
            try:
                env_file.unlink()
                console.print("[dim]Cleaned up incomplete configuration[/dim]")
            except (OSError, PermissionError) as e:
                # Ignore cleanup errors - file might be locked or permission denied
                console.print(f"[dim]Note: Could not remove .env file: {e}[/dim]")

    def _shutdown_services(self) -> None:
        """Shutdown Docker Compose services when exiting."""
        try:
            # Check if we have a configuration (services might be running)
            env_file = get_env_file_path()
            if not env_file.exists():
                return  # No config, no services to shut down

            console.print("[cyan]Shutting down SRE Agent services...[/cyan]")

            compose_file_path = get_compose_file_path(self.dev_mode)
            if not compose_file_path.exists():
                return  # No compose file, nothing to shut down

            # Reload environment to detect profiles
            from dotenv import load_dotenv

            load_dotenv(env_file, override=True)
            enabled_profiles = self._get_enabled_profiles()

            # Build docker compose down command with profiles
            cmd = ["docker", "compose", "-f", str(compose_file_path)]

            # Add --env-file if it exists
            if env_file.exists():
                cmd.extend(["--env-file", str(env_file)])

            # Add profile flags to ensure profiled services are also stopped
            for profile in enabled_profiles:
                cmd.extend(["--profile", profile])

            cmd.append("down")

            # Run docker compose down
            result = subprocess.run(  # nosec B603 B607
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                console.print("[green]✅ Services shut down successfully[/green]")
            else:
                # Don't show error details to avoid cluttering exit, just a brief note
                console.print("[yellow]⚠️  Some services may still be running[/yellow]")

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            # Ignore common subprocess errors during shutdown to avoid disrupting exit
            console.print("[yellow]⚠️  Some services may still be running[/yellow]")
        except Exception:
            # Log unexpected errors but don't disrupt exit
            console.print("[dim]Note: Error during service shutdown[/dim]")

    def _get_aws_credentials_input(self) -> str:
        """Get AWS credentials from user input."""
        console.print(
            Panel(
                "[bold]AWS Authentication Setup[/bold]\n\n"
                "To authenticate with AWS:\n"
                "1. Visit your AWS access portal\n"
                "2. Click on [cyan]`Access keys`[/cyan]\n"
                "3. From Option 2, copy the credentials\n"
                "4. Paste them in the CLI",
                border_style="blue",
                title="AWS Setup Instructions",
            )
        )

        console.print(
            "\n[cyan]Please paste your AWS credentials from the portal (Option 2):[/cyan]"
        )
        console.print("[dim]This should look like:[/dim]")
        console.print("[dim][aws_profile_name][/dim]")
        console.print("[dim]aws_access_key_id = AKIA...[/dim]")
        console.print("[dim]aws_secret_access_key = ...[/dim]")
        console.print()

        # Get credentials from user
        credentials_text = ""
        console.print("[cyan]Paste your credentials (press Enter twice when done):[/cyan]")

        while True:
            try:
                line = input()
                if line.strip() == "" and credentials_text.strip():
                    break
                credentials_text += line + "\n"
            except (EOFError, KeyboardInterrupt):
                console.print("[red]❌ Credentials input cancelled[/red]")
                console.print("[red]❌ AWS authentication setup failed[/red]")
                self._cleanup_incomplete_setup()
                console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
                sys.exit(1)

        if not credentials_text.strip():
            console.print("[red]❌ No credentials provided[/red]")
            console.print("[red]❌ AWS authentication setup failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)

        return credentials_text

    def _extract_profile_name(self, credentials_text: str) -> str:
        """Extract profile name from AWS credentials text."""
        for line in credentials_text.strip().split("\n"):
            if line.strip().startswith("[") and line.strip().endswith("]"):
                return line.strip()[1:-1]
        return "default"

    def _read_existing_credentials(self, credentials_file: Path) -> tuple[str, set[str]]:
        """Read existing AWS credentials file. Returns (content, profile_names)."""
        existing_content = ""
        existing_profiles = set()

        if credentials_file.exists():
            with open(credentials_file) as f:
                content = f.read()
                # Extract existing profile names
                for line in content.split("\n"):
                    if line.strip().startswith("[") and line.strip().endswith("]"):
                        existing_profiles.add(line.strip()[1:-1])
                existing_content = content

        return existing_content, existing_profiles

    def _write_new_profile(
        self, credentials_file: Path, existing_content: str, credentials_text: str
    ) -> None:
        """Write new AWS profile to credentials file."""
        with open(credentials_file, "w") as f:
            if existing_content and not existing_content.endswith("\n"):
                existing_content += "\n"
            f.write(existing_content + credentials_text.strip() + "\n")
        console.print(f"[green]✅ AWS credentials saved to {credentials_file}[/green]")

    def _update_existing_profile(
        self,
        credentials_file: Path,
        existing_content: str,
        profile_name: str,
        credentials_text: str,
    ) -> None:
        """Update existing AWS profile in credentials file."""
        lines = existing_content.split("\n") if existing_content else []
        new_lines = []
        in_target_profile = False

        for line in lines:
            if line.strip() == f"[{profile_name}]":
                in_target_profile = True
                new_lines.append(line)
            elif line.strip().startswith("[") and line.strip().endswith("]"):
                in_target_profile = False
                new_lines.append(line)
            elif not in_target_profile:
                new_lines.append(line)

        # Add new profile credentials
        new_lines.extend(credentials_text.strip().split("\n")[1:])  # Skip profile header

        with open(credentials_file, "w") as f:
            f.write("\n".join(new_lines) + "\n")
        console.print(f"[green]✅ AWS credentials updated in {credentials_file}[/green]")

    def _save_aws_credentials(self, credentials_text: str) -> str:
        """Parse and save AWS credentials, return the profile name."""
        profile_name = self._extract_profile_name(credentials_text)

        # Setup AWS directory and credentials file
        aws_dir = Path.home() / ".aws"
        aws_dir.mkdir(exist_ok=True)
        credentials_file = aws_dir / "credentials"

        try:
            existing_content, existing_profiles = self._read_existing_credentials(credentials_file)

            if profile_name not in existing_profiles:
                self._write_new_profile(credentials_file, existing_content, credentials_text)
            else:
                self._update_existing_profile(
                    credentials_file, existing_content, profile_name, credentials_text
                )

            console.print(f"[green]✅ Using profile: {profile_name}[/green]")
            return profile_name
        except Exception as e:
            console.print(f"[red]❌ Failed to save credentials: {e}[/red]")
            console.print("[red]❌ AWS authentication setup failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)

    def _configure_aws_region_and_cluster(self, profile_name: str) -> tuple[str, str]:
        """Configure AWS region and EKS cluster, return (region, cluster_name)."""
        from rich.prompt import Prompt

        # Get region and cluster info
        console.print("\n[cyan]AWS Region Configuration:[/cyan]")
        region = Prompt.ask("AWS Region", default="eu-west-2")

        console.print("\n[cyan]EKS Cluster Configuration:[/cyan]")
        cluster_name = Prompt.ask("EKS Cluster Name", default="")

        if not cluster_name:
            console.print("[red]❌ No cluster name provided[/red]")
            console.print("[red]❌ EKS cluster configuration failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)

        # Update environment variables
        updates = {
            "AWS_REGION": region,
            "TARGET_EKS_CLUSTER_NAME": cluster_name,
            "DEV_BEARER_TOKEN": "123",  # Default bearer token for development
            "TOOLS": '["list_pods", "get_logs", "get_file_contents", "create_issue"]',
            "PROFILES": "",  # Initialize empty profiles (Slack/Firewall disabled by default)
            # Slack defaults (required by orchestrator even if not using Slack)
            "SLACK_SIGNING_SECRET": "null",
            "SLACK_CHANNEL_ID": "null",
        }

        # Add AWS profile if it's not default
        if profile_name != "default":
            updates["AWS_PROFILE"] = profile_name

        _update_env_file(updates)
        return region, cluster_name

    def _test_aws_credentials(self, profile_name: str) -> None:
        """Test AWS credentials and exit on failure."""
        console.print(f"[cyan]Testing AWS credentials for profile '{profile_name}'...[/cyan]")

        test_cmd = ["aws", "sts", "get-caller-identity"]
        if profile_name != "default":
            test_cmd.extend(["--profile", profile_name])

        test_result = subprocess.run(  # nosec B603 B607
            test_cmd, capture_output=True, text=True, timeout=15, check=False
        )

        if test_result.returncode != 0:
            console.print(f"[red]❌ AWS credentials test failed: {test_result.stderr}[/red]")
            console.print("[red]❌ AWS cluster connection failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)
        else:
            console.print("[green]✅ AWS credentials are valid[/green]")

    def _verify_cluster_exists(self, profile_name: str, region: str, cluster_name: str) -> None:
        """Verify EKS cluster exists and exit on failure."""
        console.print(
            f"[cyan]Checking if cluster '{cluster_name}' exists in region '{region}'...[/cyan]"
        )

        describe_cmd = [
            "aws",
            "eks",
            "describe-cluster",
            "--name",
            cluster_name,
            "--region",
            region,
        ]
        if profile_name != "default":
            describe_cmd.extend(["--profile", profile_name])

        describe_result = subprocess.run(  # nosec B603 B607
            describe_cmd, capture_output=True, text=True, timeout=15, check=False
        )

        if describe_result.returncode != 0:
            console.print(
                f"[red]❌ Cluster '{cluster_name}' not found in region '{region}': "
                f"{describe_result.stderr}[/red]"
            )
            console.print("[red]❌ AWS cluster connection failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)
        else:
            console.print(f"[green]✅ Cluster '{cluster_name}' found[/green]")

    def _configure_kubectl_for_cluster(
        self, profile_name: str, region: str, cluster_name: str
    ) -> bool:
        """Configure kubectl for EKS cluster. Returns True if successful."""
        console.print(
            f"[cyan]Configuring kubectl for cluster '{cluster_name}' "
            f"using profile '{profile_name}'...[/cyan]"
        )

        aws_cmd = [
            "aws",
            "eks",
            "update-kubeconfig",
            "--region",
            region,
            "--name",
            cluster_name,
        ]

        if profile_name != "default":
            aws_cmd.extend(["--profile", profile_name])

        result = subprocess.run(  # nosec B603 B607
            aws_cmd, capture_output=True, text=True, timeout=30, check=False
        )

        if result.returncode == 0:
            console.print(f"[green]✅ kubectl configured for cluster '{cluster_name}'[/green]")
            return True
        else:
            console.print(f"[red]❌ Failed to configure kubectl: {result.stderr}[/red]")
            console.print("[red]❌ AWS cluster connection failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)

    def _test_kubectl_connection(self) -> bool:
        """Test kubectl connection and configure services. Returns True if successful."""
        kubectl_result = subprocess.run(  # nosec B603 B607
            ["kubectl", "get", "nodes", "--request-timeout=10s"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if kubectl_result.returncode == 0:
            node_count = len(
                [
                    line
                    for line in kubectl_result.stdout.strip().split("\n")
                    if line and not line.startswith("NAME")
                ]
            )
            console.print(
                f"[green]✅ Successfully connected to cluster! Found {node_count} nodes[/green]"
            )

            # Discover and select services to monitor
            selected_services = self._discover_and_select_services()
            if selected_services:
                current_updates = {"SERVICES": selected_services}
                _update_env_file(current_updates)
                console.print("[green]✅ Service monitoring configured[/green]")
            else:
                # Fallback to default if discovery fails
                current_updates = {
                    "SERVICES": '["cartservice", "adservice", "emailservice", '
                    '"frontend", "checkoutservice"]'
                }
                _update_env_file(current_updates)
                console.print("[yellow]⚠️  Using default service list[/yellow]")

            return True
        else:
            console.print(
                f"[yellow]⚠️  kubectl configured but connection test failed: "
                f"{kubectl_result.stderr}[/yellow]"
            )
            console.print("[dim]You may need to check your cluster permissions[/dim]")
            return True  # Still consider it configured

    def _test_aws_and_configure_kubectl(
        self, profile_name: str, region: str, cluster_name: str
    ) -> bool:
        """Test AWS connection and configure kubectl."""
        console.print(
            f"\n[cyan]Testing connection to cluster '{cluster_name}' in region '{region}'...[/cyan]"
        )

        try:
            self._test_aws_credentials(profile_name)
            self._verify_cluster_exists(profile_name, region, cluster_name)
            self._configure_kubectl_for_cluster(profile_name, region, cluster_name)
            return self._test_kubectl_connection()

        except subprocess.TimeoutExpired:
            console.print("[red]❌ AWS/kubectl command timed out[/red]")
            console.print("[red]❌ AWS cluster connection failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]❌ Unexpected error during AWS setup: {e}[/red]")
            console.print("[red]❌ AWS cluster connection failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)

    def _configure_aws_credentials_and_cluster(self) -> bool:
        """Configure AWS credentials using Option 2 from AWS portal and set up cluster access."""
        credentials_text = self._get_aws_credentials_input()
        profile_name = self._save_aws_credentials(credentials_text)
        region, cluster_name = self._configure_aws_region_and_cluster(profile_name)
        return self._test_aws_and_configure_kubectl(profile_name, region, cluster_name)

    def _configure_github_simple(self) -> None:
        """Simple GitHub configuration for first-time setup."""
        from rich.prompt import Prompt

        console.print(
            Panel(
                "[bold]GitHub Integration Setup[/bold]\n\n"
                "To create a GitHub Personal Access Token:\n\n"
                "1. Go to GitHub → Settings → Developer settings\n\n"
                "2. Click 'Personal access tokens' → 'Tokens (classic)'\n\n"
                "3. Click 'Generate new token (classic)' with 'repo' scope",
                border_style="blue",
                title="GitHub Setup Instructions",
            )
        )

        console.print("\n[cyan]GitHub Configuration:[/cyan]")

        org_name = Prompt.ask("GitHub Organisation/Username", default="")
        repo_name = Prompt.ask("Repository Name", default="")
        bug_folder = Prompt.ask("Folder to monitor for bugs", default="src")

        console.print("\n[dim]💡 Get your token at: https://github.com/settings/tokens[/dim]")
        pat_token = Prompt.ask("GitHub Personal Access Token", password=True, default="")

        if org_name and repo_name and pat_token:
            # Test GitHub PAT token
            console.print("[cyan]Testing GitHub PAT token...[/cyan]")
            if self._test_github_token(pat_token, org_name, repo_name):
                updates = {
                    "GITHUB_ORGANISATION": org_name,
                    "GITHUB_REPO_NAME": repo_name,
                    "PROJECT_ROOT": bug_folder,
                    "GITHUB_PERSONAL_ACCESS_TOKEN": pat_token,
                    # Ensure Slack defaults are set if not already configured
                    "SLACK_SIGNING_SECRET": os.getenv("SLACK_SIGNING_SECRET", "null"),
                    "SLACK_CHANNEL_ID": os.getenv("SLACK_CHANNEL_ID", "null"),
                    # Initialize PROFILES if not already set
                    "PROFILES": os.getenv("PROFILES", ""),
                }
                _update_env_file(updates)
                console.print("[green]✅ GitHub configuration saved[/green]")
                console.print(
                    f"[green]✅ Monitoring: {org_name}/{repo_name} (folder: {bug_folder})[/green]"
                )
            else:
                console.print("[red]❌ GitHub PAT token validation failed[/red]")
                console.print("[red]❌ GitHub configuration failed[/red]")
                self._cleanup_incomplete_setup()
                console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
                sys.exit(1)
        else:
            console.print(
                "[yellow]⚠️  Incomplete GitHub configuration. "
                "You can complete it later with 'config'.[/yellow]"
            )

    def _build_docker_compose_cmd(
        self, compose_file_path: Path, env_file_path: Path, enabled_profiles: list[str]
    ) -> list[str]:
        """Build docker compose command with appropriate flags.

        Args:
            compose_file_path: Path to compose file
            env_file_path: Path to .env file
            enabled_profiles: List of profiles to enable

        Returns:
            Complete docker compose command as list
        """
        cmd = ["docker", "compose", "-f", str(compose_file_path)]

        # Only add --env-file if it exists
        if env_file_path.exists():
            cmd.extend(["--env-file", str(env_file_path)])

        # Add profile flags for each enabled profile
        for profile in enabled_profiles:
            cmd.extend(["--profile", profile])

        cmd.extend(["up", "-d"])
        return cmd

    def _check_service_health(self, compose_file_path: Path, env_file_path: Path) -> None:
        """Check and display service health status."""
        health_cmd = ["docker", "compose", "-f", str(compose_file_path)]
        if env_file_path.exists():
            health_cmd.extend(["--env-file", str(env_file_path)])
        health_cmd.append("ps")

        health_result = subprocess.run(  # nosec B603 B607
            health_cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if health_result.returncode == 0:
            # Count services that are "Up" (running)
            running_services = [
                line
                for line in health_result.stdout.split("\n")
                if "Up " in line and "sre-agent-" in line
            ]
            console.print(f"[green]✅ {len(running_services)} services are running[/green]")

    def _test_kubernetes_aws_access(self, compose_file_path: Path, env_file_path: Path) -> None:
        """Test if kubernetes container can access AWS."""
        console.print("[cyan]Testing AWS access from kubernetes container...[/cyan]")
        aws_cmd = ["docker", "compose", "-f", str(compose_file_path)]
        if env_file_path.exists():
            aws_cmd.extend(["--env-file", str(env_file_path)])
        aws_cmd.extend(["exec", "-T", "kubernetes", "aws", "sts", "get-caller-identity"])

        aws_test_result = subprocess.run(  # nosec B603 B607
            aws_cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if aws_test_result.returncode == 0:
            console.print("[green]✅ Kubernetes container can access AWS[/green]")
        else:
            console.print(
                f"[yellow]⚠️  Kubernetes container AWS access test failed: "
                f"{aws_test_result.stderr}[/yellow]"
            )
            console.print(
                "[dim]This might affect cluster operations, but services are running[/dim]"
            )

    def _ensure_docker_is_running(self) -> bool:
        """Ensure Docker is running, with user prompts to start it."""
        while True:
            try:
                docker_result = subprocess.run(  # nosec B603 B607
                    ["docker", "info"], capture_output=True, text=True, timeout=5, check=False
                )
                if docker_result.returncode == 0:
                    console.print("[green]✅ Docker is running[/green]")
                    return True
                else:
                    # Docker is not running
                    console.print("[yellow]⚠️  Docker is not running.[/yellow]")
                    console.print("\n[cyan]Please start Docker Desktop:[/cyan]")
                    console.print("  • Open Docker Desktop application")
                    console.print("  • Wait for Docker to start (may take a minute)")
                    console.print("  • Look for the Docker whale icon in your system tray/menu bar")

                    started_docker = questionary.confirm(
                        "\nHave you started Docker?", default=True, style=sre_agent_style
                    ).ask()
                    if started_docker is None or not started_docker:
                        console.print("[red]❌ Docker is required to run SRE Agent services.[/red]")
                        console.print("[red]❌ Docker services startup failed[/red]")
                        self._cleanup_incomplete_setup()
                        console.print(
                            "[yellow]Exiting setup. "
                            "Run 'sre-agent' again when Docker is ready.[/yellow]"
                        )
                        sys.exit(1)

                    console.print("[cyan]Checking Docker status...[/cyan]")
                    # Loop will continue to check again

            except Exception:
                console.print(
                    "[red]❌ Docker is not available. Please install Docker Desktop.[/red]"
                )
                console.print("\n[cyan]Install Docker Desktop:[/cyan]")
                console.print("  • Visit: https://www.docker.com/products/docker-desktop")
                console.print("  • Download and install Docker Desktop")
                console.print("  • Start Docker Desktop")

                installed_docker = questionary.confirm(
                    "\nHave you installed and started Docker Desktop?",
                    default=False,
                    style=sre_agent_style,
                ).ask()
                if installed_docker is None or not installed_docker:
                    console.print("[red]❌ Docker is required to run SRE Agent services.[/red]")
                    console.print("[red]❌ Docker services startup failed[/red]")
                    self._cleanup_incomplete_setup()
                    console.print(
                        "[yellow]Exiting setup. "
                        "Run 'sre-agent' again when Docker is ready.[/yellow]"
                    )
                    sys.exit(1)

                console.print("[cyan]Checking Docker status...[/cyan]")
                # Loop will continue to check again

    def _start_docker_services(self) -> bool:
        """Start Docker Compose services."""
        compose_file_path = get_compose_file_path(self.dev_mode)

        if self.dev_mode:
            console.print("[yellow]🔧 Development mode: Using compose.dev.yaml[/yellow]")
        else:
            console.print("[cyan]🚀 Production mode: Using compose.agent.yaml[/cyan]")

        # Check if Docker is running - with retry option
        self._ensure_docker_is_running()

        # Check if compose file exists
        if not compose_file_path.exists():
            console.print(f"[red]❌ Docker Compose file not found: {compose_file_path}[/red]")
            console.print("[red]❌ Docker services startup failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)

        # Reload environment variables to detect latest configuration
        from dotenv import load_dotenv

        env_file_path = get_env_file_path()
        if env_file_path.exists():
            load_dotenv(env_file_path, override=True)

        # Determine which profiles to enable
        enabled_profiles = self._get_enabled_profiles()

        # Show which profiles are being enabled
        if enabled_profiles:
            profile_list = ", ".join(enabled_profiles)
            console.print(f"[cyan]Enabling optional services: {profile_list}[/cyan]")

        try:
            # Build and execute docker compose command
            cmd = self._build_docker_compose_cmd(compose_file_path, env_file_path, enabled_profiles)

            # Start services in detached mode with progress spinner
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=False,
                console=console,
            ) as progress:
                compose_name = "compose.dev.yaml" if self.dev_mode else "compose.agent.yaml"
                progress.add_task(f"Building SRE Agent with {compose_name}...", total=None)
                result = subprocess.run(  # nosec B603 B607
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # Extended to 5 minutes
                    check=False,
                )

            if result.returncode == 0:
                console.print("[green]✅ Services started successfully![/green]")

                # Wait a moment for services to initialize
                import time

                console.print("[cyan]Waiting for services to initialize...[/cyan]")
                time.sleep(10)  # Give more time for containers to start

                # Check service health
                self._check_service_health(compose_file_path, env_file_path)

                # Test AWS access
                self._test_kubernetes_aws_access(compose_file_path, env_file_path)

                return True
            else:
                console.print(f"[red]❌ Failed to start services: {result.stderr}[/red]")
                console.print("[red]❌ Docker services startup failed[/red]")
                self._cleanup_incomplete_setup()
                console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
                sys.exit(1)

        except Exception as e:
            console.print(f"[red]❌ Error starting services: {e}[/red]")
            console.print("[red]❌ Docker services startup failed[/red]")
            self._cleanup_incomplete_setup()
            console.print("[yellow]Exiting setup. Run 'sre-agent' again to retry.[/yellow]")
            sys.exit(1)

    def _create_status_panel(self) -> Panel:
        """Create the status panel showing current context."""
        status_table = Table(show_header=False, box=None, padding=(0, 1))

        # Check if we have essential configuration
        has_aws_config = bool(os.getenv("TARGET_EKS_CLUSTER_NAME") and os.getenv("AWS_REGION"))
        has_bearer_token = bool(os.getenv("DEV_BEARER_TOKEN"))

        # Connection status
        if has_aws_config and has_bearer_token:
            cluster_name = os.getenv("TARGET_EKS_CLUSTER_NAME", "Unknown")
            namespace = "default"
            status_table.add_row(
                "[green]●[/green]", f"Connected to: [cyan]{cluster_name} ({namespace})[/cyan]"
            )
        else:
            status_table.add_row(
                "[red]●[/red]", "[yellow]Not configured - run 'config' to set up[/yellow]"
            )

        # Quick help
        status_table.add_row(
            "[dim]💡[/dim]", "[dim]Type 'help' for commands or 'exit' to quit[/dim]"
        )

        return Panel(
            status_table,
            title="[bold cyan]SRE Agent v0.0.1[/bold cyan]",
            border_style="cyan",
            padding=(0, 1),
        )

    def _get_prompt_style(self) -> Style:
        """Get the prompt styling for prompt_toolkit."""
        return Style.from_dict(
            {
                "prompt.sre-agent": "bold cyan",
                "prompt.separator": "dim",
            }
        )

    def cmdloop(self, intro: Optional[str] = None) -> None:
        """Override cmdloop to use rich formatting."""
        # Run first-time setup if needed
        if self.is_first_run:
            console.print("[bright_cyan]Starting configuration setup...[/bright_cyan]")
            console.print()
            setup_completed = self._run_first_time_setup()
            console.print()

            if setup_completed:
                console.print("[dim]Entering interactive shell...[/dim]")
            else:
                console.print(
                    "[dim]Entering interactive shell. Use 'config' to set up credentials.[/dim]"
                )
            console.print()

        # Show initial status
        console.print(self._create_status_panel())
        console.print()

        while True:
            try:
                # Create prompt with command history navigation
                prompt_parts = FormattedText(
                    [("class:prompt.sre-agent", "sre-agent"), ("class:prompt.separator", "> ")]
                )

                # Get user input with command history navigation
                try:
                    line = self.prompt_session.prompt(prompt_parts, style=self._get_prompt_style())
                except EOFError:
                    self._shutdown_services()
                    console.print("\n👋 Goodbye!")
                    break
                except KeyboardInterrupt:
                    console.print("\n^C")
                    continue

                line = line.strip()
                if not line:
                    continue

                # Handle exit commands
                if line.lower() in ("exit", "quit", "q"):
                    self._shutdown_services()
                    console.print("👋 Goodbye!")
                    break

                # Process the command
                self.onecmd(line)

            except KeyboardInterrupt:
                self._shutdown_services()
                console.print("\n👋 Goodbye!")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    def do_help(self, arg: str) -> None:
        """Show help information."""
        if not arg:
            # Show general help
            console.print(
                Panel(
                    "[bold cyan]🤖 SRE Agent Interactive Shell[/bold cyan]\n\n"
                    "Your AI-powered Site Reliability Engineering assistant.",
                    border_style="cyan",
                    title="Help",
                )
            )

            # Create commands table
            commands_table = Table(show_header=True, header_style="bold cyan")
            commands_table.add_column("Command", style="bright_cyan", width=20)
            commands_table.add_column("Description", width=60)

            commands_table.add_row("diagnose [service]", "Diagnose issues with a specific service")
            commands_table.add_row("config", "Open interactive configuration menu")
            commands_table.add_row("status", "Show current connection and configuration status")
            commands_table.add_row("clear", "Clear the screen")
            commands_table.add_row("help [command]", "Show help for a specific command")
            commands_table.add_row("exit/quit", "Exit the SRE Agent shell")

            console.print("\n")
            console.print(
                Panel(
                    commands_table,
                    title="[bold yellow]📋 Available Commands[/bold yellow]",
                    border_style="yellow",
                )
            )

            # Examples
            examples_table = Table(show_header=True, header_style="bold green")
            examples_table.add_column("Example", style="bright_green", width=30)
            examples_table.add_column("Description", width=50)

            examples_table.add_row("diagnose frontend", "Diagnose the frontend service")
            examples_table.add_row(
                "diagnose cartservice --cluster prod", "Diagnose with specific cluster"
            )
            examples_table.add_row("config", "Configure AWS, GitHub, Slack, etc.")
            examples_table.add_row("status", "Check current configuration")

            console.print("\n")
            console.print(
                Panel(
                    examples_table,
                    title="[bold green]💡 Usage Examples[/bold green]",
                    border_style="green",
                )
            )
        elif arg == "diagnose":
            # Show help for specific command
            console.print(
                Panel(
                    "[bold]diagnose [service] [options][/bold]\n\n"
                    "Diagnose issues with a specific service using AI analysis.\n\n"
                    "[cyan]Options:[/cyan]\n"
                    "  --cluster, -c    Kubernetes cluster name\n"
                    "  --namespace, -n  Kubernetes namespace\n"
                    "  --timeout, -t    Request timeout in seconds\n"
                    "  --output, -o     Output format (rich/json/plain)\n\n"
                    "[cyan]Examples:[/cyan]\n"
                    "  diagnose frontend\n"
                    "  diagnose cartservice --cluster prod --namespace production",
                    title="[bold cyan]Diagnose Command Help[/bold cyan]",
                    border_style="cyan",
                )
            )
        elif arg == "config":
            console.print(
                Panel(
                    "[bold]config[/bold]\n\n"
                    "Open the interactive configuration menu to set up:\n"
                    "• AWS Kubernetes cluster settings\n"
                    "• GitHub integration\n"
                    "• Slack notifications\n"
                    "• LLM Firewall\n"
                    "• Model provider selection",
                    title="[bold cyan]Config Command Help[/bold cyan]",
                    border_style="cyan",
                )
            )
        else:
            console.print(f"[yellow]No help available for '{arg}'[/yellow]")

        console.print()

    def _validate_diagnose_input(self, arg: str) -> Optional[list[str]]:
        """Validate and parse diagnose command input. Returns args list or None if error."""
        if not arg.strip():
            console.print("[red]Error: Service name required[/red]")
            console.print("Usage: diagnose [service] [options]")
            console.print("Example: diagnose frontend")
            return None

        try:
            args = shlex.split(arg)
        except ValueError as e:
            console.print(f"[red]Error parsing arguments: {e}[/red]")
            return None

        if not args:
            console.print("[red]Error: Service name required[/red]")
            return None

        return args

    def _parse_option_value(self, args: list[str], i: int, option_name: str) -> Optional[str]:
        """Parse option value from args. Returns value or None if invalid."""
        if i + 1 >= len(args):
            console.print(f"[red]{option_name} requires a value[/red]")
            return None
        return args[i + 1]

    def _parse_cluster_option(self, args: list[str], i: int) -> Optional[str]:
        """Parse cluster option."""
        return self._parse_option_value(args, i, "--cluster")

    def _parse_namespace_option(self, args: list[str], i: int) -> Optional[str]:
        """Parse namespace option."""
        return self._parse_option_value(args, i, "--namespace")

    def _parse_timeout_option(self, args: list[str], i: int) -> Optional[int]:
        """Parse timeout option."""
        timeout_str = self._parse_option_value(args, i, "--timeout")
        if timeout_str is None:
            return None
        try:
            return int(timeout_str)
        except ValueError:
            console.print(f"[red]Invalid timeout value: {timeout_str}[/red]")
            return None

    def _parse_output_option(self, args: list[str], i: int) -> Optional[str]:
        """Parse output option."""
        output = self._parse_option_value(args, i, "--output")
        if output is None:
            return None
        if output not in ("rich", "json", "plain"):
            console.print(f"[red]Invalid output format: {output}[/red]")
            return None
        return output

    def _parse_diagnose_options(
        self, args: list[str]
    ) -> Optional[tuple[Optional[str], str, int, str]]:
        """Parse diagnose options.

        Returns (cluster, namespace, timeout, output) or None if error.
        """
        cluster = None
        namespace = "default"
        timeout = 300
        output = "rich"

        i = 1
        while i < len(args):
            if args[i] in ("--cluster", "-c"):
                cluster = self._parse_cluster_option(args, i)
                if cluster is None:
                    return None
            elif args[i] in ("--namespace", "-n"):
                parsed_namespace = self._parse_namespace_option(args, i)
                if parsed_namespace is None:
                    return None
                namespace = parsed_namespace
            elif args[i] in ("--timeout", "-t"):
                parsed_timeout = self._parse_timeout_option(args, i)
                if parsed_timeout is None:
                    return None
                timeout = parsed_timeout
            elif args[i] in ("--output", "-o"):
                parsed_output = self._parse_output_option(args, i)
                if parsed_output is None:
                    return None
                output = parsed_output
            else:
                console.print(f"[red]Unknown option: {args[i]}[/red]")
                return None
            i += 2

        return cluster, namespace, timeout, output

    def _parse_diagnose_args(self, arg: str) -> Optional[tuple[str, Optional[str], str, int, str]]:
        """Parse diagnose command arguments.

        Returns (service, cluster, namespace, timeout, output) or None if error.
        """
        args = self._validate_diagnose_input(arg)
        if not args:
            return None

        service = args[0]
        options = self._parse_diagnose_options(args)
        if not options:
            return None

        cluster, namespace, timeout, output = options
        return service, cluster, namespace, timeout, output

    def _validate_diagnose_config(self) -> Optional[str]:
        """Validate configuration for diagnosis. Returns bearer token or None if error."""
        # Check configuration
        if not self.config:
            console.print("[red]Configuration not loaded. Run 'config' first.[/red]")
            return None

        # Get bearer token
        bearer_token = get_bearer_token_from_env()
        if not bearer_token:
            console.print(
                "[red]DEV_BEARER_TOKEN not found in environment. "
                "Make sure it's set in your .env file.[/red]"
            )
            return None

        if not self.config.api_url:
            console.print("[red]API URL not configured. Run 'config' first.[/red]")
            return None

        return bearer_token

    def do_diagnose(self, arg: str) -> None:
        """Diagnose issues with a service."""
        parsed_args = self._parse_diagnose_args(arg)
        if not parsed_args:
            return

        service, cluster, namespace, timeout, output = parsed_args

        bearer_token = self._validate_diagnose_config()
        if not bearer_token:
            return

        # Use defaults from config
        cluster = cluster or getattr(self.config, "default_cluster", None)
        namespace = namespace or getattr(self.config, "default_namespace", "default")

        # Show diagnosis info
        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_row("[cyan]Service:[/cyan]", service)
        if cluster:
            info_table.add_row("[cyan]Cluster:[/cyan]", cluster)
        info_table.add_row("[cyan]Namespace:[/cyan]", namespace)

        console.print(
            Panel(
                info_table,
                title="[bold blue]🔍 Starting Diagnosis[/bold blue]",
                border_style="blue",
            )
        )

        # Run diagnosis
        if self.config is None:
            console.print("[red]Configuration not loaded. Run 'config' first.[/red]")
            return

        try:
            asyncio.run(
                _run_diagnosis(
                    self.config, bearer_token, service, cluster, namespace, timeout, output
                )
            )
        except Exception as e:
            console.print(f"[red]Diagnosis failed: {e}[/red]")

        console.print()

    def _handle_menu_choice(self, normalised_choice: str) -> bool:
        """Handle a single menu choice.

        Args:
            normalised_choice: The normalised menu choice string

        Returns:
            True if should exit menu, False otherwise
        """
        if normalised_choice == "AWS Kubernetes Cluster":
            _configure_aws_cluster()
        elif normalised_choice == "GitHub Repository Access":
            _configure_github()
        elif normalised_choice == "Slack Notification":
            _configure_slack()
        elif normalised_choice == "LLM Firewall":
            _configure_llm_firewall()
        elif normalised_choice == "Model Provider Settings":
            _configure_model_provider()
        elif normalised_choice == "View Config":
            _view_current_config()
        elif normalised_choice == "Reset Config":
            _reset_configuration()
        elif normalised_choice == "Exit Menu":
            console.print("[cyan]Exiting configuration menu...[/cyan]")
            return True

        console.print("\n" + "─" * 80 + "\n")
        return False

    def _handle_profile_changes(self, initial_profiles: set[str]) -> None:
        """Handle profile changes after configuration menu exits.

        Args:
            initial_profiles: Set of profiles enabled before menu
        """
        from dotenv import load_dotenv

        env_file = get_env_file_path()
        if env_file.exists():
            load_dotenv(env_file, override=True)  # Reload to get latest values
        current_profiles = set(self._get_enabled_profiles())

        if current_profiles != initial_profiles:
            # Profiles changed!
            added = current_profiles - initial_profiles
            removed = initial_profiles - current_profiles

            console.print("\n[yellow]⚠️  Optional services configuration changed:[/yellow]")
            if added:
                console.print(f"  [green]+ Enabled: {', '.join(added)}[/green]")
            if removed:
                console.print(f"  [red]- Disabled: {', '.join(removed)}[/red]")

            # Only offer restart if services are running
            if self._are_services_running():
                restart = questionary.confirm(
                    "Restart services to apply changes?", default=True, style=sre_agent_style
                ).ask()

                if restart:
                    if self._restart_services_with_profiles():
                        console.print("[green]✅ Services restarted successfully![/green]")
                    else:
                        console.print("[red]❌ Service restart failed[/red]")
                        console.print("[dim]You can try restarting manually later[/dim]")
            else:
                console.print("[dim]Services will use new configuration on next start[/dim]")

    def do_config(self, arg: str) -> None:
        """Open configuration menu."""
        console.print()

        # Track initial profile state BEFORE menu
        from dotenv import load_dotenv

        env_file = get_env_file_path()
        if env_file.exists():
            load_dotenv(env_file, override=True)
        initial_profiles = set(self._get_enabled_profiles())

        # Import and run config menu functions
        from .commands.config import _print_config_header

        _print_config_header()

        # Run config menu loop
        while True:
            choice = _display_main_menu()
            normalised_choice = _normalise_choice(choice)
            should_exit = self._handle_menu_choice(normalised_choice)
            if should_exit:
                break

        # Handle profile changes after menu exits
        self._handle_profile_changes(initial_profiles)

        # Reload config after changes
        self._load_config()
        console.print()

    def do_status(self, arg: str) -> None:
        """Show current status and configuration."""
        console.print(self._create_status_panel())

        # Show environment file status
        env_file = get_env_file_path()
        if env_file.exists():
            console.print(f"[green]✅ Environment file found: {env_file}[/green]")
        else:
            console.print(f"[yellow]⚠️  No environment file found: {env_file}[/yellow]")
            console.print("[dim]Run 'config' to set up your configuration[/dim]")

        console.print()

    def do_clear(self, arg: str) -> None:
        """Clear the screen."""
        os.system("clear" if os.name == "posix" else "cls")  # nosec B605
        console.print(self._create_status_panel())
        console.print()

    def do_exit(self, arg: str) -> bool:
        """Exit the SRE Agent shell."""
        self._shutdown_services()
        console.print("👋 Goodbye!")
        return True

    def do_quit(self, arg: str) -> bool:
        """Exit the SRE Agent shell."""
        return self.do_exit(arg)

    def do_q(self, arg: str) -> bool:
        """Exit the SRE Agent shell."""
        return self.do_exit(arg)

    def emptyline(self) -> bool:
        """Handle empty line input."""
        return False  # Don't repeat the last command

    def default(self, line: str) -> None:
        """Handle unknown commands."""
        console.print(f"[red]Unknown command: {line}[/red]")
        console.print("[dim]Type 'help' for available commands[/dim]")


def start_interactive_shell(dev_mode: bool = False) -> None:
    """Start the interactive SRE Agent shell."""
    shell = None
    try:
        shell = SREAgentShell(dev_mode=dev_mode)
        shell.cmdloop()
    except KeyboardInterrupt:
        if shell:
            shell._shutdown_services()
        console.print("\n👋 Goodbye!")
    except Exception as e:
        if shell:
            shell._shutdown_services()
        console.print(f"[red]Shell error: {e}[/red]")
        sys.exit(1)
