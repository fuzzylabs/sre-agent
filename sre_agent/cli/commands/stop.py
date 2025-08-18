"""Stop command for SRE Agent services."""

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
def stop(platform: str):
    """Stop the SRE Agent services.

    This will gracefully shut down all SRE Agent microservices.
    """
    manager = ServiceManager(platform)

    console.print(
        Panel(
            f"[bold red]🛑 Stopping SRE Agent Services[/bold red]\n\n"
            f"Platform: {platform.upper()}\n"
            f"Compose File: {manager.compose_file}",
            border_style="red",
        )
    )

    if manager.stop_services():
        console.print("\n[green]🎉 All services stopped successfully![/green]")
    else:
        console.print("\n[red]❌ Some services may still be running.[/red]")
