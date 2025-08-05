"""Diagnose command for SRE Agent CLI."""

import asyncio
import json
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ..utils.config import load_config, ConfigError

console = Console()


@click.command()
@click.option('--service', '-s', required=True, help='Service name to diagnose')
@click.option('--cluster', '-c', help='Kubernetes cluster name')
@click.option('--namespace', '-n', help='Kubernetes namespace')
@click.option('--timeout', '-t', type=int, help='Request timeout in seconds')
@click.option('--output', '-o', type=click.Choice(['rich', 'json', 'plain']), help='Output format')
@click.option('--follow', '-f', is_flag=True, help='Follow the diagnosis in real-time')
@click.pass_context
def diagnose(ctx, service: str, cluster: Optional[str], namespace: Optional[str], 
            timeout: Optional[int], output: Optional[str], follow: bool):
    """
    Diagnose issues with a specific service.
    
    This command triggers an AI-powered diagnosis of your service, analyzing
    logs, configurations, and related resources to identify potential issues.
    
    Examples:
    
      # Basic service diagnosis
      sre-agent diagnose --service myapp
      
      # Diagnose with specific cluster and namespace
      sre-agent diagnose --service myapp --cluster prod --namespace production
      
      # Follow diagnosis in real-time
      sre-agent diagnose --service myapp --follow
    """
    try:
        config = ctx.obj['config']
    except (KeyError, TypeError):
        console.print("[red]Configuration not loaded. Run 'sre-agent config setup' first.[/red]")
        return
    
    # Use command-line options or fall back to config defaults
    cluster = cluster or config.default_cluster
    namespace = namespace or config.default_namespace
    timeout = timeout or config.default_timeout
    output = output or config.output_format
    
    # Validate required configuration
    if not config.bearer_token:
        console.print("[red]Bearer token not configured. Run 'sre-agent config setup' first.[/red]")
        return
    
    if not config.api_url:
        console.print("[red]API URL not configured. Run 'sre-agent config setup' first.[/red]")
        return
    
    # Show diagnosis info
    info_table = Table(show_header=False, box=None, padding=(0, 1))
    info_table.add_row("[cyan]Service:[/cyan]", service)
    if cluster:
        info_table.add_row("[cyan]Cluster:[/cyan]", cluster)
    info_table.add_row("[cyan]Namespace:[/cyan]", namespace)
    
    console.print(Panel(
        info_table,
        title="[bold blue]🔍 Starting Diagnosis[/bold blue]",
        border_style="blue"
    ))
    
    # Run the diagnosis
    asyncio.run(_run_diagnosis(config, service, cluster, namespace, timeout, output, follow))


async def _run_diagnosis(config, service: str, cluster: Optional[str], namespace: str, 
                        timeout: int, output: str, follow: bool):
    """Run the actual diagnosis request."""
    
    # Prepare request payload
    payload = {"text": service}
    if cluster:
        payload["cluster"] = cluster
    if namespace != "default":
        payload["namespace"] = namespace
    
    headers = {
        "Authorization": f"Bearer {config.bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    url = f"{config.api_url.rstrip('/')}/diagnose"
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if follow:
                await _follow_diagnosis(client, url, headers, payload, output)
            else:
                await _single_diagnosis(client, url, headers, payload, output)
                
    except httpx.TimeoutException:
        console.print(f"[red]Request timed out after {timeout} seconds[/red]")
    except httpx.ConnectError:
        console.print(f"[red]Failed to connect to SRE Agent API at {config.api_url}[/red]")
        console.print("[yellow]Make sure the SRE Agent services are running[/yellow]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")


async def _single_diagnosis(client: httpx.AsyncClient, url: str, headers: dict, 
                           payload: dict, output: str):
    """Run a single diagnosis request."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running AI diagnosis...", total=None)
        
        try:
            response = await client.post(url, json=payload, headers=headers)
            progress.remove_task(task)
            
            if response.status_code == 200:
                result = response.json()
                _display_diagnosis_result(result, output)
            elif response.status_code == 401:
                console.print("[red]Authentication failed. Check your bearer token.[/red]")
            elif response.status_code == 404:
                console.print("[red]Service not found or API endpoint unavailable.[/red]")
            else:
                console.print(f"[red]Request failed with status {response.status_code}[/red]")
                if response.text:
                    console.print(f"[red]{response.text}[/red]")
                    
        except Exception as e:
            progress.remove_task(task)
            raise e


async def _follow_diagnosis(client: httpx.AsyncClient, url: str, headers: dict, 
                           payload: dict, output: str):
    """Follow diagnosis with real-time updates (if supported by API)."""
    # For now, fall back to single diagnosis
    # In the future, this could use SSE or WebSocket for real-time updates
    console.print("[yellow]Real-time following not yet implemented, running single diagnosis...[/yellow]")
    await _single_diagnosis(client, url, headers, payload, output)


def _display_diagnosis_result(result: dict, output: str):
    """Display the diagnosis result in the specified format."""
    
    if output == "json":
        console.print(json.dumps(result, indent=2))
        return
    elif output == "plain":
        console.print(str(result))
        return
    
    # Rich output (default)
    console.print()
    
    if "error" in result:
        console.print(Panel(
            f"[red]{result['error']}[/red]",
            title="[bold red]❌ Diagnosis Failed[/bold red]",
            border_style="red"
        ))
        return
    
    # Success case - display structured results
    if "diagnosis" in result:
        diagnosis_text = Text(result["diagnosis"])
        console.print(Panel(
            diagnosis_text,
            title="[bold green]✅ Diagnosis Complete[/bold green]",
            border_style="green"
        ))
    
    # Show additional details if available
    if "details" in result:
        details_table = Table(show_header=True, header_style="bold cyan")
        details_table.add_column("Component")
        details_table.add_column("Status")
        details_table.add_column("Details")
        
        for detail in result["details"]:
            status_style = "green" if detail.get("status") == "healthy" else "red"
            details_table.add_row(
                detail.get("component", "Unknown"),
                f"[{status_style}]{detail.get('status', 'Unknown')}[/{status_style}]",
                detail.get("message", "")
            )
        
        console.print("\n")
        console.print(Panel(
            details_table,
            title="[bold cyan]📊 Component Analysis[/bold cyan]",
            border_style="cyan"
        ))
    
    # Show recommendations if available
    if "recommendations" in result and result["recommendations"]:
        recommendations_text = "\n".join([f"• {rec}" for rec in result["recommendations"]])
        console.print("\n")
        console.print(Panel(
            recommendations_text,
            title="[bold yellow]💡 Recommendations[/bold yellow]",
            border_style="yellow"
        ))
    
    console.print("\n[dim]Diagnosis completed successfully![/dim]")