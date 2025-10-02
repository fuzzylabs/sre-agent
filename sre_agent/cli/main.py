#!/usr/bin/env python3
"""SRE Agent CLI - Your AI-powered Site Reliability Engineering assistant.

A powerful command-line interface for diagnosing, monitoring, and managing
your infrastructure with AI-powered insights.
"""

import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .commands.config import config
from .commands.diagnose import diagnose
from .commands.help import help_cmd
from .interactive_shell import start_interactive_shell
from .utils.ascii_art import get_ascii_art
from .utils.config import ConfigError, load_config
from .utils.paths import get_env_file_path

console = Console()


def print_banner() -> None:
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
@click.option("--dev", is_flag=True, help="Use development compose file (compose.dev.yaml)")
@click.pass_context
def cli(ctx: click.Context, version: bool, config_path: Optional[str], dev: bool) -> None:
    """SRE Agent - Your AI-powered Site Reliability Engineering assistant.

    Use AI to diagnose issues, monitor services, and debug problems across
    your Kubernetes clusters, GitHub repositories, and Slack channels.
    """
    if version:
        from . import __version__

        console.print(f"SRE Agent CLI version {__version__}")
        return

    # Show banner and enter interactive mode if no command specified
    if ctx.invoked_subcommand is None:
        print_banner()

        # Check if this is first run (no .env file exists)
        env_file = get_env_file_path()
        if not env_file.exists():
            console.print("\n[bright_yellow]👋 Welcome to SRE Agent![/bright_yellow]")
            console.print("[dim]It looks like this is your first time running SRE Agent.[/dim]")
            console.print()
        else:
            console.print("\n[bright_cyan]Starting interactive shell...[/bright_cyan]")
            console.print("[dim]💡 Type 'help' for available commands or 'exit' to quit[/dim]")
            console.print()

        # Start interactive shell
        start_interactive_shell(dev_mode=dev)
        return

    # Load configuration
    try:
        config_data = load_config(config_path)
        ctx.ensure_object(dict)
        ctx.obj["config"] = config_data
    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("[yellow]Run 'sre-agent config' to configure the CLI[/yellow]")
        sys.exit(1)


# Add commands
cli.add_command(diagnose)
cli.add_command(config)
cli.add_command(help_cmd, name="help")


def main() -> None:
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
