"""Local running mode for the CLI."""

import math
import shutil
import subprocess  # nosec B404
import sys

import questionary
from rich.panel import Panel

from sre_agent.cli.mode.paths import project_root
from sre_agent.cli.presentation.console import console


def run_local_mode() -> None:
    """Run the agent locally."""
    console.print("[cyan]Local run[/cyan]")
    console.print("[dim]This runs the agent using your local environment.[/dim]")

    log_group = questionary.text(
        "CloudWatch log group:",
        validate=lambda value: True if value.strip() else "Log group is required.",
    ).ask()
    if not log_group:
        return
    _ensure_slack_mcp_running()
    _start_local_shell(log_group)


def _ensure_slack_mcp_running() -> None:
    """Start the Slack MCP server container if needed."""
    console.print("[cyan]Ensuring Slack MCP server is running...[/cyan]")
    compose_cmd = _docker_compose_cmd()
    if compose_cmd is None:
        console.print("[yellow]Docker Compose not found. Start Slack MCP manually.[/yellow]")
        console.print("Run: `docker compose up -d slack`")
        return

    result = subprocess.run(
        [*compose_cmd, "up", "-d", "slack"],
        cwd=project_root(),
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603
    if result.returncode != 0:
        console.print("[yellow]Could not start Slack MCP server automatically.[/yellow]")
        console.print("Run: `docker compose up -d slack`")


def _docker_compose_cmd() -> list[str] | None:
    """Return the docker compose command.

    Returns:
        The docker compose command parts, or None when unavailable.
    """
    docker_path = shutil.which("docker")
    if docker_path:
        result = subprocess.run(
            [docker_path, "compose", "version"],
            check=False,
            capture_output=True,
            text=True,
        )  # nosec B603
        if result.returncode == 0:
            return [docker_path, "compose"]
    docker_compose_path = shutil.which("docker-compose")
    if docker_compose_path:
        return [docker_compose_path]
    return None


def _start_local_shell(log_group: str) -> None:
    """Start a local interactive shell for diagnoses.

    Args:
        log_group: CloudWatch log group name.
    """
    _print_local_banner(log_group)
    while True:
        try:
            command = input("sre-agent (local)> ")
        except EOFError:
            console.print()
            return

        command = command.strip()
        if not command:
            continue

        if command in {"exit", "quit"}:
            console.print("[dim]Exiting local shell.[/dim]")
            return

        if command == "help":
            _print_local_help()
            continue

        if command.startswith("diagnose "):
            _handle_diagnose_command(log_group, command)
            continue

        console.print("[yellow]Unknown command. Type 'help' for commands.[/yellow]")


def _print_local_banner(log_group: str) -> None:
    """Print the local shell banner.

    Args:
        log_group: CloudWatch log group name.
    """
    console.print(
        Panel(
            "Starting interactive shell...\nType 'help' for available commands or 'exit' to quit.",
            title="Local Mode",
            border_style="cyan",
        )
    )
    console.print(f"[green]Connected to: {log_group}[/green]")
    console.print("[dim]Slack MCP is required for local diagnostics.[/dim]")
    console.print("\n[bold]Example command:[/bold]")
    console.print("diagnose currencyservice 10m")


def _print_local_help() -> None:
    """Print local shell help."""
    console.print("[bold]Commands:[/bold]")
    console.print("- diagnose <service> [duration]")
    console.print("  Examples: diagnose currencyservice 10m, diagnose cartservice 5")
    console.print("- help")
    console.print("- exit")


def _handle_diagnose_command(log_group: str, command: str) -> None:
    """Parse and run a diagnose command.

    Args:
        log_group: CloudWatch log group name.
        command: Raw command string.
    """
    parts = command.split()
    if len(parts) < 2:
        console.print("[yellow]Usage: diagnose <service> [duration][/yellow]")
        return

    service_name = parts[1].strip()
    if not service_name:
        console.print("[yellow]Service name is required.[/yellow]")
        return

    duration = parts[2] if len(parts) > 2 else "10m"
    minutes = _parse_duration_minutes(duration)
    if minutes is None:
        console.print("[yellow]Invalid duration. Use 10m, 1h, or minutes like 5.[/yellow]")
        return

    console.print(f"[cyan]Running diagnosis for {service_name} (last {minutes} minutes)...[/cyan]")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sre_agent.run",
            log_group,
            service_name,
            str(minutes),
        ],
        check=False,
    )  # nosec B603


def _parse_duration_minutes(value: str) -> int | None:
    """Parse a duration string into minutes.

    Args:
        value: Duration input from the user.

    Returns:
        Duration in minutes, or None when invalid.
    """
    raw = value.strip().lower()
    minutes: int | None = None
    if raw.isdigit():
        minutes = int(raw)
    else:
        unit = raw[-1]
        number = raw[:-1]
        if number.isdigit():
            amount = int(number)
            if amount > 0:
                if unit == "m":
                    minutes = amount
                elif unit == "h":
                    minutes = amount * 60
                elif unit == "s":
                    minutes = max(1, math.ceil(amount / 60))

    if minutes is None or minutes <= 0:
        return None
    return minutes
