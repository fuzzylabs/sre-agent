"""Start command for SRE Agent services."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..utils.service_manager import ServiceManager

console = Console()


@click.command()
@click.option(
    "--platform",
    type=click.Choice(["aws", "gcp", "ecr", "gar"]),
    default="aws",
    help="Platform to use for services",
)
@click.option("--build", is_flag=True, help="Build images before starting")
@click.option("--detached", "-d", is_flag=True, default=True, help="Run in detached mode")
@click.option("--wait", is_flag=True, help="Wait for services to become healthy")
@click.option(
    "--minimal",
    is_flag=True,
    default=True,
    help="Use minimal service configuration (core services only)",
)
def start(  # noqa: PLR0912
    platform: str, build: bool, detached: bool, wait: bool, minimal: bool
) -> None:
    """Start the SRE Agent services.

    This will start the SRE Agent microservices:
    - Orchestrator (main API)
    - LLM Server (AI text generation)
    - Kubernetes MCP Server
    - GitHub MCP Server
    - Prompt Server

    By default, uses minimal configuration (no Slack, no Llama Firewall).
    Use --no-minimal for full configuration with all services.

    Examples:
      # Start with AWS configuration (minimal by default)
      sre-agent start --platform aws

      # Start with full configuration
      sre-agent start --platform aws --no-minimal

      # Build and start services
      sre-agent start --build

      # Start and wait for health checks
      sre-agent start --wait
    """
    manager = ServiceManager(platform)

    # Use minimal compose file if requested
    if minimal:
        manager.compose_file = f"compose.minimal.{platform}.yaml"
        manager._load_services_from_compose()  # Reload services for the new compose file
        console.print(f"[debug] Using minimal compose file: {manager.compose_file}")
    else:
        console.print(f"[debug] Using full compose file: {manager.compose_file}")

    # Pre-flight checks
    if not manager.check_docker_compose():
        console.print("[red]❌ Docker Compose not found. Please install Docker.[/red]")
        return

    if not manager.check_compose_file():
        console.print(f"[red]❌ Compose file not found: {manager.compose_file}[/red]")
        console.print("Available files:")
        for f in Path(".").glob("compose.*.yaml"):
            console.print(f"  • {f.name}")
        return

    # Show startup info
    info_table = Table(show_header=False, box=None, padding=(0, 1))
    info_table.add_row("[cyan]Platform:[/cyan]", platform.upper())
    info_table.add_row("[cyan]Compose File:[/cyan]", manager.compose_file)
    info_table.add_row("[cyan]Build Images:[/cyan]", "✅ Yes" if build else "❌ No")
    info_table.add_row("[cyan]Detached Mode:[/cyan]", "✅ Yes" if detached else "❌ No")

    console.print(
        Panel(
            info_table,
            title="[bold blue]🚀 Starting SRE Agent Services[/bold blue]",
            border_style="blue",
        )
    )

    # Start services
    if manager.start_services(build=build, detached=detached):
        if wait and detached:
            # For minimal mode, skip detailed health checks since services are already healthy
            if minimal:
                console.print("\n[green]🎉 Services started successfully![/green]")
                console.print("\n[cyan]Ready to use:[/cyan]")
                console.print("  • API: [dim]http://localhost:8003[/dim]")
                console.print("  • Health: [dim]curl http://localhost:8003/health[/dim]")
                console.print("  • Diagnose: [dim]sre-agent diagnose --service myapp[/dim]")
            else:
                import asyncio

                status = asyncio.run(manager.wait_for_services())

                healthy_count = sum(1 for s in status.values() if s)
                total_count = len(status)

                if healthy_count == total_count:
                    console.print("\n[green]🎉 Orchestrator service is healthy![/green]")
                    console.print("\n[cyan]Ready to use:[/cyan]")
                    console.print("  • API: [dim]http://localhost:8003[/dim]")
                    console.print("  • Health: [dim]curl http://localhost:8003/health[/dim]")
                    console.print("  • Diagnose: [dim]sre-agent diagnose --service myapp[/dim]")
                else:
                    console.print("\n[yellow]⚠️  Orchestrator service is not healthy[/yellow]")
                    console.print("Check logs: [dim]sre-agent logs[/dim]")

        elif not detached:
            console.print("\n[green]Services started in foreground mode.[/green]")
            console.print("Press Ctrl+C to stop services.")
    else:
        console.print("\n[red]❌ Failed to start services. Check the logs above.[/red]")
