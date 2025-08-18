"""Service manager for SRE Agent services."""

import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Optional

import httpx
from rich.console import Console
from rich.live import Live
from rich.table import Table

console = Console()


class ServiceManager:
    """Manage SRE Agent services startup and health checking."""

    def __init__(self, platform: str = "aws"):
        self.platform = platform
        self.compose_file = f"compose.{platform}.yaml"
        self._load_services_from_compose()

    def _load_services_from_compose(self):
        """Dynamically load services from the compose file."""
        # Define service ports based on compose file configuration
        self.service_ports = {
            "orchestrator": 8003,  # Exposed on host port 8003
            "llm-server": 8000,  # Internal port 8000
            "llama-firewall": 8000,  # Internal port 8000
            "kubernetes": 3001,  # Internal port 3001
            "github": 3001,  # Internal port 3001
            "slack": 3001,  # Internal port 3001
            "prompt-server": 3001,  # Internal port 3001
        }

        # Determine services based on compose file name
        if "minimal" in self.compose_file:
            # Minimal compose files only include core services
            self.services = [
                "kubernetes",
                "github",
                "prompt-server",
                "llm-server",
                "orchestrator",
            ]
        else:
            # Full compose files include all services
            self.services = [
                "slack",
                "kubernetes",
                "github",
                "prompt-server",
                "llm-server",
                "llama-firewall",
                "orchestrator",
            ]

    def check_docker_compose(self) -> bool:
        """Check if docker compose is available."""
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except:
            return False

    def check_compose_file(self) -> bool:
        """Check if the compose file exists."""
        return Path(self.compose_file).exists()

    def start_services(self, build: bool = False, detached: bool = True) -> bool:
        """Start the SRE Agent services."""
        cmd = ["docker", "compose", "-f", self.compose_file, "up"]

        if build:
            cmd.append("--build")
        if detached:
            cmd.append("-d")

        try:
            console.print(
                f"[cyan]Starting SRE Agent services with {self.compose_file}...[/cyan]"
            )
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                console.print("[green]✅ Services started successfully![/green]")
                return True
            else:
                console.print("[red]❌ Failed to start services:[/red]")
                console.print(result.stderr)
                return False

        except subprocess.TimeoutExpired:
            console.print("[red]❌ Timeout starting services (5 minutes)[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Error starting services: {e}[/red]")
            return False

    def stop_services(self) -> bool:
        """Stop the SRE Agent services."""
        try:
            console.print("[cyan]Stopping SRE Agent services...[/cyan]")
            result = subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "down"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                console.print("[green]✅ Services stopped successfully![/green]")
                return True
            else:
                console.print("[red]❌ Failed to stop services:[/red]")
                console.print(result.stderr)
                return False

        except Exception as e:
            console.print(f"[red]❌ Error stopping services: {e}[/red]")
            return False

    async def check_service_health(
        self, service: str, port: int, max_retries: int = 10
    ) -> bool:
        """Check if a service is healthy."""
        health_endpoints = {
            "orchestrator": "http://localhost:8003/health",
            "llm-server": "http://localhost:8000/health",
            "llama-firewall": "http://localhost:8000/health",
            "prompt-server": "http://localhost:3001/health",
        }

        # Services that only support socket checks (MCP servers)
        socket_only_services = {"kubernetes", "github", "slack"}

        if service in health_endpoints:
            # Services with HTTP health endpoints
            url = health_endpoints[service]

            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        response = await client.get(url)
                        if response.status_code == 200:
                            return True
                except:
                    pass

                await asyncio.sleep(1)

            return False
        elif service in socket_only_services:
            # MCP servers that only support socket checks
            for attempt in range(max_retries):
                try:
                    import socket

                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        result = s.connect_ex(("localhost", port))
                        if result == 0:
                            return True
                except:
                    pass

                await asyncio.sleep(1)

            return False
        else:
            # Fallback: try HTTP first, then socket check
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=3) as client:
                        # Try to connect to the service on its port
                        response = await client.get(
                            f"http://localhost:{port}/", timeout=3
                        )
                        # If we get any response (even 404), the service is up
                        return True
                except:
                    # If HTTP fails, fall back to socket check
                    try:
                        import socket

                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(1)
                            result = s.connect_ex(("localhost", port))
                            if result == 0:
                                return True
                    except:
                        pass

                await asyncio.sleep(1)

            return False

    async def wait_for_services(self) -> Dict[str, bool]:
        """Wait for all services to become healthy."""
        console.print("\n[cyan]Waiting for services to become healthy...[/cyan]")

        # Create status display
        def create_status_table():
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Service", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Port")

            # Only show orchestrator for health check
            table.add_row("orchestrator", "[yellow]⏳ Starting...[/yellow]", "8003")

            return table

        service_status = {"orchestrator": False}

        # Check only orchestrator service
        async def check_orchestrator():
            healthy = await self.check_service_health("orchestrator", 8003)
            service_status["orchestrator"] = healthy
            return healthy

        with Live(create_status_table(), console=console, refresh_per_second=2) as live:
            # Start checking orchestrator
            result = await check_orchestrator()

            # Update display with result
            final_table = Table(show_header=True, header_style="bold cyan")
            final_table.add_column("Service", style="cyan")
            final_table.add_column("Status", justify="center")
            final_table.add_column("Port")

            if result:
                final_table.add_row("orchestrator", "[green]✅ Healthy[/green]", "8003")
            else:
                final_table.add_row("orchestrator", "[red]❌ Unhealthy[/red]", "8003")

            live.update(final_table)

        return service_status

    def get_service_logs(self, service: Optional[str] = None, lines: int = 50) -> str:
        """Get logs from services."""
        cmd = [
            "docker",
            "compose",
            "-f",
            self.compose_file,
            "logs",
            "--tail",
            str(lines),
        ]
        if service:
            cmd.append(service)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"Error getting logs: {e}"
