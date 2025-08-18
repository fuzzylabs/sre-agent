"""Status command for SRE Agent services."""

import subprocess

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
def status(platform: str):
    """Check the status of SRE Agent services.

    Shows which services are running and their health status.
    """
    import asyncio

    manager = ServiceManager(platform)

    console.print(
        Panel(
            f"[bold cyan]📊 Service Status Check[/bold cyan]\n\n"
            f"Platform: {platform.upper()}\n"
            f"Compose File: {manager.compose_file}",
            border_style="cyan",
        )
    )

    # Check if services are running
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", manager.compose_file, "ps"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            console.print("\n[cyan]Docker Compose Status:[/cyan]")
            console.print(result.stdout)
        else:
            console.print("\n[red]❌ Could not get Docker Compose status[/red]")
            return
    except Exception as e:
        console.print(f"\n[red]❌ Error checking status: {e}[/red]")
        return

    # Check service health
    console.print("\n[cyan]Checking service health...[/cyan]")
    status_dict = asyncio.run(manager.wait_for_services())

    healthy_count = sum(1 for s in status_dict.values() if s)
    total_count = len(status_dict)

    if healthy_count == total_count:
        console.print(f"\n[green]🎉 All {total_count} services are healthy![/green]")
    else:
        console.print(
            f"\n[yellow]⚠️  {healthy_count}/{total_count} services healthy[/yellow]"
        )
        console.print("Run 'sre-agent logs' to investigate issues.")
