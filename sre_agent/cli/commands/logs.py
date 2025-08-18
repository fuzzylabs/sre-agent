"""Logs command for SRE Agent services."""

import subprocess
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from ..utils.service_manager import ServiceManager

console = Console()


@click.command()
@click.option(
    "--platform",
    type=click.Choice(["aws", "gcp", "ecr", "gar"]),
    default="aws",
    help="Platform used for services",
)
@click.option("--service", help="Specific service to show logs for")
@click.option("--lines", "-n", type=int, default=50, help="Number of log lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
def logs(platform: str, service: Optional[str], lines: int, follow: bool):
    """Show logs from SRE Agent services.

    Examples:
      # Show all service logs
      sre-agent logs

      # Show logs for specific service
      sre-agent logs --service orchestrator

      # Follow logs in real-time
      sre-agent logs --follow
    """
    manager = ServiceManager(platform)

    if follow:
        # Use docker compose logs -f directly
        cmd = ["docker", "compose", "-f", manager.compose_file, "logs", "-f"]
        if service:
            cmd.append(service)

        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n[yellow]Log following stopped.[/yellow]")
    else:
        logs_output = manager.get_service_logs(service, lines)
        console.print(
            Panel(
                logs_output,
                title=f"[bold cyan]📋 Service Logs ({service or 'all services'})[/bold cyan]",
                border_style="cyan",
            )
        )
