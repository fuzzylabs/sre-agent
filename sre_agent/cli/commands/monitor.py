"""Monitor command for SRE Agent CLI."""

import asyncio
import time
from datetime import datetime
from typing import Any, Optional

import click
import httpx
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from sre_agent.cli.utils.config import SREAgentConfig

console = Console()


class ServiceMonitor:
    """Monitor for SRE Agent services and resources."""

    def __init__(
        self, config: SREAgentConfig, namespace: str = "default", cluster: Optional[str] = None
    ) -> None:
        """Initialise the service monitor.

        Args:
            config: The SRE Agent configuration object.
            namespace: The Kubernetes namespace. Defaults to "default".
            cluster: The Kubernetes cluster name. Defaults to None.
        """
        self.config = config
        self.namespace = namespace
        self.cluster = cluster
        self.monitoring: bool = False
        self.last_check: Optional[str] = None
        self.service_status: dict[str, Any] = {}

    async def start_monitoring(
        self,
        watch: bool = False,
        interval: int = 30,
        services: Optional[list[str]] = None,
        max_duration: Optional[int] = None,
    ) -> None:
        """Start monitoring services."""
        self.monitoring = True
        start_time = time.time()

        console.print(
            Panel(
                f"[bold cyan]🔍 Starting Service Monitoring[/bold cyan]\n\n"
                f"Namespace: [yellow]{self.namespace}[/yellow]\n"
                f"Cluster: [yellow]{self.cluster or 'default'}[/yellow]\n"
                f"Interval: [yellow]{interval}s[/yellow]\n"
                f"Services: [yellow]{', '.join(services) if services else 'all'}[/yellow]",
                border_style="cyan",
            )
        )

        if watch:
            await self._watch_mode(interval, services, max_duration, start_time)
        else:
            await self._single_check(services)

    async def _single_check(self, services: Optional[list[str]]) -> None:
        """Perform a single monitoring check."""
        console.print("\n[cyan]Performing health check...[/cyan]")

        try:
            status = await self._check_services(services)
            self._display_status(status)
        except Exception as e:
            console.print(f"[red]Monitoring failed: {e}[/red]")

    async def _watch_mode(
        self,
        interval: int,
        services: Optional[list[str]],
        max_duration: Optional[int],
        start_time: float,
    ) -> None:
        """Run in continuous watch mode."""

        def create_status_display() -> Table:
            """Create the status display table."""
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Service", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Last Check", style="dim")
            table.add_column("Issues", style="yellow")

            if not self.service_status:
                table.add_row("No services monitored yet", "-", "-", "-")
                return table

            for service_name, status in self.service_status.items():
                status_style = "green" if status.get("healthy", False) else "red"
                status_text = "✅ Healthy" if status.get("healthy", False) else "❌ Issues"

                issues = status.get("issues", [])
                issues_text = f"{len(issues)} issues" if issues else "None"

                last_check = status.get("last_check", "Never")

                table.add_row(
                    service_name,
                    f"[{status_style}]{status_text}[/{status_style}]",
                    last_check,
                    issues_text,
                )

            return table

        try:
            with Live(create_status_display(), console=console, refresh_per_second=1) as live:
                check_count = 0

                while self.monitoring:
                    # Check if max duration exceeded
                    if max_duration and (time.time() - start_time) > max_duration:
                        console.print(
                            f"\n[yellow]Maximum monitoring duration "
                            f"({max_duration}s) reached.[/yellow]"
                        )
                        break

                    try:
                        # Perform health check
                        status = await self._check_services(services)
                        self.service_status.update(status)
                        self.last_check = datetime.now().strftime("%H:%M:%S")

                        # Update display
                        live.update(create_status_display())

                        check_count += 1

                        # Wait for next check
                        await asyncio.sleep(interval)

                    except KeyboardInterrupt:
                        self.monitoring = False
                        break
                    except Exception as e:
                        console.print(f"\n[red]Error during monitoring: {e}[/red]")
                        await asyncio.sleep(5)  # Wait before retry

        except KeyboardInterrupt:
            pass
        finally:
            self.monitoring = False
            console.print(f"\n[yellow]Monitoring stopped after {check_count} checks.[/yellow]")

    async def _check_services(self, services: Optional[list[str]]) -> dict[str, Any]:
        """Check the health of specified services."""
        # For now, we'll use the health endpoint to check overall system health
        # In a more advanced implementation, this could query specific services
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.config.bearer_token}",
            "Accept": "application/json",
        }

        health_url = f"{self.config.api_url.rstrip('/')}/health"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(health_url, headers=headers)

                if response.status_code == 200:  # noqa: PLR2004
                    health_data = response.json()
                    return self._parse_health_response(health_data, services)
                else:
                    return {
                        "system": {
                            "healthy": False,
                            "issues": [f"API returned {response.status_code}"],
                            "last_check": datetime.now().strftime("%H:%M:%S"),
                        }
                    }

        except httpx.ConnectError:
            return {
                "system": {
                    "healthy": False,
                    "issues": ["Cannot connect to SRE Agent API"],
                    "last_check": datetime.now().strftime("%H:%M:%S"),
                }
            }
        except Exception as e:
            return {
                "system": {
                    "healthy": False,
                    "issues": [str(e)],
                    "last_check": datetime.now().strftime("%H:%M:%S"),
                }
            }

    def _parse_health_response(
        self, health_data: dict[str, Any], services: Optional[list[str]]
    ) -> dict[str, Any]:
        """Parse health response into service status."""
        current_time = datetime.now().strftime("%H:%M:%S")

        # If specific services requested, filter for those
        if services:
            # This is a placeholder - in reality, you'd filter based on actual service data
            result: dict[str, Any] = {}
            for service in services:
                result[service] = {
                    "healthy": health_data.get("status") == "healthy",
                    "issues": []
                    if health_data.get("status") == "healthy"
                    else ["Service status unknown"],
                    "last_check": current_time,
                }
            return result
        else:
            # Return overall system status
            return {
                "system": {
                    "healthy": health_data.get("status") == "healthy",
                    "issues": []
                    if health_data.get("status") == "healthy"
                    else health_data.get("issues", ["Unknown issues"]),
                    "last_check": current_time,
                }
            }

    def _display_status(self, status: dict[str, Any]) -> None:
        """Display service status in a formatted way."""
        for service_name, service_status in status.items():
            is_healthy = service_status.get("healthy", False)
            issues = service_status.get("issues", [])

            # Create status panel
            if is_healthy:
                panel_style = "green"
                status_text = "✅ Healthy"
                content = (
                    f"[green]{status_text}[/green]\n\n"
                    f"Last check: {service_status.get('last_check', 'Unknown')}"
                )
            else:
                panel_style = "red"
                status_text = "❌ Issues Detected"
                issues_text = "\n".join([f"• {issue}" for issue in issues])
                content = (
                    f"[red]{status_text}[/red]\n\n[yellow]Issues:[/yellow]\n{issues_text}\n\n"
                    f"Last check: {service_status.get('last_check', 'Unknown')}"
                )

            console.print(
                Panel(
                    content,
                    title=f"[bold]{service_name.title()}[/bold]",
                    border_style=panel_style,
                )
            )


@click.command()
@click.option("--watch", "-w", is_flag=True, help="Continuously monitor services")
@click.option("--namespace", "-n", help="Kubernetes namespace to monitor")
@click.option("--cluster", "-c", help="Kubernetes cluster name")
@click.option("--interval", "-i", type=int, help="Check interval in seconds (watch mode only)")
@click.option("--services", "-s", multiple=True, help="Specific services to monitor")
@click.option("--duration", "-d", type=int, help="Maximum monitoring duration in seconds")
@click.option("--output", "-o", type=click.Choice(["rich", "json", "plain"]), help="Output format")
@click.pass_context
def monitor(  # noqa: PLR0913
    ctx: click.Context,
    watch: bool,
    namespace: Optional[str],
    cluster: Optional[str],
    interval: Optional[int],
    services: tuple[str, ...],
    duration: Optional[int],
    output: Optional[str],
) -> None:
    """Monitor services and infrastructure health.

    This command allows you to monitor the health of your services and
    infrastructure components, either as a one-time check or continuously.

    Examples:
      # Single health check
      sre-agent monitor

      # Continuous monitoring
      sre-agent monitor --watch

      # Monitor specific namespace with custom interval
      sre-agent monitor --watch --namespace production --interval 60

      # Monitor specific services
      sre-agent monitor --services myapp --services database --watch

      # Monitor for a specific duration
      sre-agent monitor --watch --duration 300  # 5 minutes
    """
    try:
        config = ctx.obj["config"]
    except (KeyError, TypeError):
        console.print("[red]Configuration not loaded. Run 'sre-agent config setup' first.[/red]")
        return

    # Validate required configuration
    if not config.bearer_token:
        console.print("[red]Bearer token not configured. Run 'sre-agent config setup' first.[/red]")
        return

    if not config.api_url:
        console.print("[red]API URL not configured. Run 'sre-agent config setup' first.[/red]")
        return

    # Use command-line options or fall back to config defaults
    namespace = namespace or config.default_namespace
    cluster = cluster or config.default_cluster
    interval = interval or config.monitor_interval
    output = output or config.output_format

    # Convert services tuple to list
    services_list: Optional[list[str]] = list(services) if services else None

    # Show monitoring info
    if watch:
        console.print("[cyan]Starting continuous monitoring (Ctrl+C to stop)...[/cyan]")
        if duration:
            console.print(f"[dim]Will stop automatically after {duration} seconds[/dim]")

    # Create and start monitor
    monitor_instance = ServiceMonitor(config, namespace, cluster)

    try:
        asyncio.run(
            monitor_instance.start_monitoring(
                watch=watch,
                interval=interval,
                services=services_list,
                max_duration=duration,
            )
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user.[/yellow]")
