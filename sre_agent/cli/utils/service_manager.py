"""Service manager for SRE Agent services.

Security Note: All subprocess calls use hardcoded commands with no user input
to prevent command injection attacks. Bandit B603 warnings are suppressed
with nosec comments where appropriate.
"""

import asyncio
import subprocess  # nosec B404
from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console
from rich.live import Live
from rich.table import Table

console = Console()


class ServiceManager:
    """Manage SRE Agent services startup and health checking."""

    def __init__(self, platform: str = "aws"):
        """Initialise the service manager."""
        self.platform = platform
        self.compose_file = f"compose.{platform}.yaml"
        self._load_services_from_compose()

    def _load_services_from_compose(self) -> None:
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
            result = subprocess.run(  # nosec B603 B607
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:  # nosec B110
            return False

    def check_compose_file(self) -> bool:
        """Check if the compose file exists."""
        return Path(self.compose_file).exists()

    def start_services(
        self, build: bool = False, detached: bool = True, profiles: Optional[list[str]] = None
    ) -> bool:
        """Start the SRE Agent services.

        Args:
            build: Whether to rebuild images before starting
            detached: Whether to run in detached mode
            profiles: Optional list of Docker Compose profiles to enable

        Returns:
            True if services started successfully
        """
        cmd = ["docker", "compose", "-f", self.compose_file]

        # Add profile flags
        if profiles:
            for profile in profiles:
                cmd.extend(["--profile", profile])

        cmd.append("up")

        if build:
            cmd.append("--build")
        if detached:
            cmd.append("-d")

        try:
            console.print(f"[cyan]Starting SRE Agent services with {self.compose_file}...[/cyan]")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, check=False
            )  # nosec B603 B607

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
            result = subprocess.run(  # nosec B603 B607
                ["docker", "compose", "-f", self.compose_file, "down"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
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

    def _is_http_health_service(self, service: str) -> bool:
        """Check if a service supports HTTP health endpoints."""
        health_endpoints = {
            "orchestrator": "http://localhost:8003/health",
            "llm-server": "http://localhost:8000/health",
            "llama-firewall": "http://localhost:8000/health",
            "prompt-server": "http://localhost:3001/health",
        }
        return service in health_endpoints

    def _is_socket_only_service(self, service: str) -> bool:
        """Check if a service only supports socket checks (MCP servers)."""
        socket_only_services = {"kubernetes", "github", "slack"}
        return service in socket_only_services

    def _get_health_endpoint(self, service: str) -> str:
        """Get the health endpoint URL for a service."""
        health_endpoints = {
            "orchestrator": "http://localhost:8003/health",
            "llm-server": "http://localhost:8000/health",
            "llama-firewall": "http://localhost:8000/health",
            "prompt-server": "http://localhost:3001/health",
        }
        return health_endpoints[service]

    async def _check_http_health(self, url: str, max_retries: int) -> bool:
        """Check HTTP health endpoint with retries."""
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(url)
                    if response.status_code == 200:  # noqa: PLR2004
                        return True
            except Exception:  # nosec B110
                pass

            await asyncio.sleep(1)

        return False

    def _check_socket_health(self, port: int, max_retries: int) -> bool:
        """Check socket health with retries."""
        for attempt in range(max_retries):
            try:
                import socket

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(("localhost", port))
                    if result == 0:
                        return True
            except Exception:  # nosec B110
                pass

            # Note: We can't use asyncio.sleep here since this is a sync method
            # The caller will handle the retry timing
            pass

        return False

    async def _check_socket_health_async(self, port: int, max_retries: int) -> bool:
        """Check socket health asynchronously with retries."""
        for attempt in range(max_retries):
            try:
                import socket

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(("localhost", port))
                    if result == 0:
                        return True
            except Exception:  # nosec B110
                pass

            await asyncio.sleep(1)

        return False

    async def _check_fallback_health(self, port: int, max_retries: int) -> bool:
        """Fallback health check: try HTTP first, then socket."""
        for attempt in range(max_retries):
            try:
                # Try HTTP first
                async with httpx.AsyncClient(timeout=3) as client:
                    await client.get(f"http://localhost:{port}/", timeout=3)
                    # If we get any response (even 404), the service is up
                    return True
            except Exception:  # nosec B110
                # If HTTP fails, fall back to socket check
                try:
                    import socket

                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        result = s.connect_ex(("localhost", port))
                        if result == 0:
                            return True
                except Exception:  # nosec B110
                    pass

            await asyncio.sleep(1)

        return False

    async def check_service_health(self, service: str, port: int, max_retries: int = 10) -> bool:
        """Check if a service is healthy."""
        if self._is_http_health_service(service):
            # Services with HTTP health endpoints
            url = self._get_health_endpoint(service)
            return await self._check_http_health(url, max_retries)

        elif self._is_socket_only_service(service):
            # MCP servers that only support socket checks
            return await self._check_socket_health_async(port, max_retries)

        else:
            # Fallback: try HTTP first, then socket check
            return await self._check_fallback_health(port, max_retries)

    async def wait_for_services(self) -> dict[str, bool]:
        """Wait for all services to become healthy."""
        console.print("\n[cyan]Waiting for services to become healthy...[/cyan]")

        # Create status display
        def create_status_table() -> Table:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Service", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Port")

            # Only show orchestrator for health check
            table.add_row("orchestrator", "[yellow]⏳ Starting...[/yellow]", "8003")

            return table

        service_status = {"orchestrator": False}

        # Check only orchestrator service
        async def check_orchestrator() -> bool:
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
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=False
            )  # nosec B603 B607
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"Error getting logs: {e}"
