#!/usr/bin/env python3
"""SRE Agent CLI - Your AI-powered Site Reliability Engineering assistant.

A powerful command-line interface for diagnosing, monitoring, and managing
your infrastructure with AI-powered insights.
"""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .commands.config import config
from .commands.diagnose import diagnose
from .commands.interactive import interactive
from .commands.logs import logs
from .commands.monitor import monitor
from .commands.platform import platform
from .commands.start import start
from .commands.status import status
from .commands.stop import stop
from .utils.ascii_art import get_ascii_art
from .utils.config import ConfigError, load_config

console = Console()


def print_banner():
    """Print the SRE Agent banner with ASCII art."""
    ascii_art = get_ascii_art()

    # Create a gradient effect for the ASCII art
    text = Text()
    lines = ascii_art.split("\n")

    colors = ["bright_cyan", "cyan", "blue", "bright_blue"]

    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        text.append(line + "\n", style=color)

    # Add tagline
    text.append(
        "\n🚀 Your AI-powered Site Reliability Engineering assistant\n",
        style="bright_white",
    )
    text.append("   Diagnose • Monitor • Debug • Scale\n", style="dim white")

    panel = Panel(
        text,
        border_style="bright_cyan",
        padding=(1, 2),
        title="[bold bright_cyan]Welcome to SRE Agent[/bold bright_cyan]",
        title_align="center",
    )

    console.print(panel)


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version information")
@click.option("--config-path", help="Path to configuration file")
@click.pass_context
def cli(ctx, version, config_path):
    """SRE Agent - Your AI-powered Site Reliability Engineering assistant.

    Use AI to diagnose issues, monitor services, and debug problems across
    your Kubernetes clusters, GitHub repositories, and Slack channels.
    """
    if version:
        from . import __version__

        console.print(f"SRE Agent CLI version {__version__}")
        return

    # Show banner if no command specified
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print("\n[bright_yellow]💡 Quick start (2 steps):[/bright_yellow]")
        console.print(
            "  [bright_cyan]1.[/bright_cyan] [cyan]sre-agent config setup[/cyan]           # Quick setup (essential features)"
        )
        console.print(
            "  [bright_cyan]2.[/bright_cyan] [cyan]sre-agent diagnose --service myapp[/cyan]  # Start debugging!"
        )
        console.print("\n[bright_yellow]💬 Interactive mode:[/bright_yellow]")
        console.print("  [cyan]sre-agent interactive[/cyan]")
        console.print("\n[dim]Use --help with any command for more details.[/dim]")
        return

    # Load configuration
    try:
        config_data = load_config(config_path)
        ctx.ensure_object(dict)
        ctx.obj["config"] = config_data
    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print(
            "[yellow]Run 'sre-agent config setup' to configure the CLI[/yellow]"
        )
        sys.exit(1)


# Add commands
cli.add_command(diagnose)
cli.add_command(interactive)
cli.add_command(monitor)
cli.add_command(config)
cli.add_command(platform)
cli.add_command(start)
cli.add_command(stop)
cli.add_command(status)
cli.add_command(logs)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
