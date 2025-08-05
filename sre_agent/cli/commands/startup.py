"""Startup command to launch SRE Agent services."""

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.live import Live
from rich.text import Text

console = Console()


class ServiceManager:
    """Manage SRE Agent services startup and health checking."""
    
    def __init__(self, platform: str = "aws"):
        self.platform = platform
        self.compose_file = f"compose.{platform}.yaml"
        self.services = [
            "slack", "kubernetes", "github", "prompt-server", 
            "llm-server", "llama-firewall", "orchestrator"
        ]
        self.service_ports = {
            "orchestrator": 8003,
            "llm-server": 8000,
            "llama-firewall": 8000,
            "kubernetes": 3001,
            "github": 3001,
            "slack": 3001,
            "prompt-server": 3001
        }
    
    def check_docker_compose(self) -> bool:
        """Check if docker compose is available."""
        try:
            result = subprocess.run(['docker', 'compose', 'version'], 
                                  capture_output=True, text=True, timeout=10)
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
        cmd = ['docker', 'compose', '-f', self.compose_file, 'up']
        
        if build:
            cmd.append('--build')
        if detached:
            cmd.append('-d')
        
        try:
            console.print(f"[cyan]Starting SRE Agent services with {self.compose_file}...[/cyan]")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                console.print("[green]✅ Services started successfully![/green]")
                return True
            else:
                console.print(f"[red]❌ Failed to start services:[/red]")
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
            result = subprocess.run(['docker', 'compose', '-f', self.compose_file, 'down'], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                console.print("[green]✅ Services stopped successfully![/green]")
                return True
            else:
                console.print(f"[red]❌ Failed to stop services:[/red]")
                console.print(result.stderr)
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Error stopping services: {e}[/red]")
            return False
    
    async def check_service_health(self, service: str, port: int, max_retries: int = 30) -> bool:
        """Check if a service is healthy."""
        health_endpoints = {
            "orchestrator": "http://localhost:8003/health",
            "llm-server": "http://localhost:8000/health",
            "llama-firewall": "http://localhost:8000/health"
        }
        
        if service in health_endpoints:
            url = health_endpoints[service]
            
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        response = await client.get(url)
                        if response.status_code == 200:
                            return True
                except:
                    pass
                
                await asyncio.sleep(2)
            
            return False
        else:
            # For other services, just check if port is open
            import socket
            for attempt in range(max_retries):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        result = s.connect_ex(('localhost', port))
                        if result == 0:
                            return True
                except:
                    pass
                
                time.sleep(2)
            
            return False
    
    async def wait_for_services(self) -> Dict[str, bool]:
        """Wait for all services to become healthy."""
        import asyncio
        
        console.print("\n[cyan]Waiting for services to become healthy...[/cyan]")
        
        # Create status display
        def create_status_table():
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Service", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Port")
            
            for service in self.services:
                port = self.service_ports.get(service, "N/A")
                table.add_row(service, "[yellow]⏳ Starting...[/yellow]", str(port))
            
            return table
        
        service_status = {service: False for service in self.services}
        
        # Check services in parallel
        async def check_service(service: str):
            port = self.service_ports.get(service)
            if port:
                healthy = await self.check_service_health(service, port)
                service_status[service] = healthy
                return healthy
            return False
        
        with Live(create_status_table(), console=console, refresh_per_second=2) as live:
            # Start checking all services
            tasks = [check_service(service) for service in self.services]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update display with results
            final_table = Table(show_header=True, header_style="bold cyan")
            final_table.add_column("Service", style="cyan")
            final_table.add_column("Status", justify="center")
            final_table.add_column("Port")
            
            for i, service in enumerate(self.services):
                port = self.service_ports.get(service, "N/A")
                if isinstance(results[i], bool) and results[i]:
                    final_table.add_row(service, "[green]✅ Healthy[/green]", str(port))
                else:
                    final_table.add_row(service, "[red]❌ Unhealthy[/red]", str(port))
            
            live.update(final_table)
        
        return service_status
    
    def get_service_logs(self, service: Optional[str] = None, lines: int = 50) -> str:
        """Get logs from services."""
        cmd = ['docker', 'compose', '-f', self.compose_file, 'logs', '--tail', str(lines)]
        if service:
            cmd.append(service)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"Error getting logs: {e}"


@click.group()
def startup():
    """
    Manage SRE Agent services startup and shutdown.
    
    This command helps you start, stop, and monitor the SRE Agent microservices
    that power the AI-driven debugging and monitoring capabilities.
    """
    pass


@startup.command()
@click.option('--platform', type=click.Choice(['aws', 'gcp', 'ecr', 'gar']), 
              default='aws', help='Platform to use for services')
@click.option('--build', is_flag=True, help='Build images before starting')
@click.option('--detached', '-d', is_flag=True, default=True, help='Run in detached mode')
@click.option('--wait', is_flag=True, help='Wait for services to become healthy')
def start(platform: str, build: bool, detached: bool, wait: bool):
    """
    Start the SRE Agent services.
    
    This will start all the microservices needed for the SRE Agent to function:
    - Orchestrator (main API)
    - LLM Server (AI text generation)
    - Kubernetes MCP Server
    - GitHub MCP Server  
    - Slack MCP Server
    - Prompt Server
    - Llama Firewall (security)
    
    Examples:
    
      # Start with AWS configuration
      sre-agent startup start --platform aws
      
      # Build and start services
      sre-agent startup start --build
      
      # Start and wait for health checks
      sre-agent startup start --wait
    """
    manager = ServiceManager(platform)
    
    # Pre-flight checks
    if not manager.check_docker_compose():
        console.print("[red]❌ Docker Compose not found. Please install Docker.[/red]")
        return
    
    if not manager.check_compose_file():
        console.print(f"[red]❌ Compose file not found: {manager.compose_file}[/red]")
        console.print("Available files:")
        for f in Path('.').glob('compose.*.yaml'):
            console.print(f"  • {f.name}")
        return
    
    # Show startup info
    info_table = Table(show_header=False, box=None, padding=(0, 1))
    info_table.add_row("[cyan]Platform:[/cyan]", platform.upper())
    info_table.add_row("[cyan]Compose File:[/cyan]", manager.compose_file)
    info_table.add_row("[cyan]Build Images:[/cyan]", "✅ Yes" if build else "❌ No")
    info_table.add_row("[cyan]Detached Mode:[/cyan]", "✅ Yes" if detached else "❌ No")
    
    console.print(Panel(
        info_table,
        title="[bold blue]🚀 Starting SRE Agent Services[/bold blue]",
        border_style="blue"
    ))
    
    # Start services
    if manager.start_services(build=build, detached=detached):
        if wait and detached:
            import asyncio
            status = asyncio.run(manager.wait_for_services())
            
            healthy_count = sum(1 for s in status.values() if s)
            total_count = len(status)
            
            if healthy_count == total_count:
                console.print(f"\n[green]🎉 All {total_count} services are healthy![/green]")
                console.print("\n[cyan]Ready to use:[/cyan]")
                console.print("  • API: [dim]http://localhost:8003[/dim]")
                console.print("  • Health: [dim]curl http://localhost:8003/health[/dim]")
                console.print("  • Diagnose: [dim]sre-agent diagnose --service myapp[/dim]")
            else:
                console.print(f"\n[yellow]⚠️  {healthy_count}/{total_count} services healthy[/yellow]")
                console.print("Check logs: [dim]sre-agent startup logs[/dim]")
        
        elif not detached:
            console.print("\n[green]Services started in foreground mode.[/green]")
            console.print("Press Ctrl+C to stop services.")
    else:
        console.print("\n[red]❌ Failed to start services. Check the logs above.[/red]")


@startup.command()
@click.option('--platform', type=click.Choice(['aws', 'gcp', 'ecr', 'gar']), 
              default='aws', help='Platform used for services')
def stop(platform: str):
    """
    Stop the SRE Agent services.
    
    This will gracefully shut down all SRE Agent microservices.
    """
    manager = ServiceManager(platform)
    
    console.print(Panel(
        f"[bold red]🛑 Stopping SRE Agent Services[/bold red]\n\n"
        f"Platform: {platform.upper()}\n"
        f"Compose File: {manager.compose_file}",
        border_style="red"
    ))
    
    if manager.stop_services():
        console.print("\n[green]🎉 All services stopped successfully![/green]")
    else:
        console.print("\n[red]❌ Some services may still be running.[/red]")


@startup.command()
@click.option('--platform', type=click.Choice(['aws', 'gcp', 'ecr', 'gar']), 
              default='aws', help='Platform used for services')
@click.option('--service', help='Specific service to show logs for')
@click.option('--lines', '-n', type=int, default=50, help='Number of log lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
def logs(platform: str, service: Optional[str], lines: int, follow: bool):
    """
    Show logs from SRE Agent services.
    
    Examples:
    
      # Show all service logs
      sre-agent startup logs
      
      # Show logs for specific service
      sre-agent startup logs --service orchestrator
      
      # Follow logs in real-time
      sre-agent startup logs --follow
    """
    manager = ServiceManager(platform)
    
    if follow:
        # Use docker compose logs -f directly
        cmd = ['docker', 'compose', '-f', manager.compose_file, 'logs', '-f']
        if service:
            cmd.append(service)
        
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n[yellow]Log following stopped.[/yellow]")
    else:
        logs_output = manager.get_service_logs(service, lines)
        console.print(Panel(
            logs_output,
            title=f"[bold cyan]📋 Service Logs ({service or 'all services'})[/bold cyan]",
            border_style="cyan"
        ))


@startup.command()
@click.option('--platform', type=click.Choice(['aws', 'gcp', 'ecr', 'gar']), 
              default='aws', help='Platform used for services')
def status(platform: str):
    """
    Check the status of SRE Agent services.
    
    Shows which services are running and their health status.
    """
    import asyncio
    
    manager = ServiceManager(platform)
    
    console.print(Panel(
        f"[bold cyan]📊 Service Status Check[/bold cyan]\n\n"
        f"Platform: {platform.upper()}\n"
        f"Compose File: {manager.compose_file}",
        border_style="cyan"
    ))
    
    # Check if services are running
    try:
        result = subprocess.run(['docker', 'compose', '-f', manager.compose_file, 'ps'], 
                              capture_output=True, text=True, timeout=10)
        
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
        console.print(f"\n[yellow]⚠️  {healthy_count}/{total_count} services healthy[/yellow]")
        console.print("Run 'sre-agent startup logs' to investigate issues.")