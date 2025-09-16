"""Help command for SRE Agent CLI."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.command()
def help_cmd() -> None:
    """Display help information for SRE Agent CLI commands.

    Shows available commands and their usage examples.
    """
    console.print(
        Panel(
            "[bold cyan]🤖 SRE Agent CLI - AI-powered Site Reliability Engineering[/bold cyan]\n\n"
            "Your intelligent assistant for diagnosing and managing infrastructure issues.",
            border_style="cyan",
            title="SRE Agent CLI",
            title_align="center",
        )
    )

    # Create commands table
    commands_table = Table(show_header=True, header_style="bold cyan")
    commands_table.add_column("Command", style="bright_cyan", width=20)
    commands_table.add_column("Description", width=60)

    commands_table.add_row(
        "sre-agent diagnose [service]", "Diagnose issues with a specific service using AI analysis"
    )
    commands_table.add_row("sre-agent config", "Open interactive configuration menu for settings")
    commands_table.add_row("sre-agent help", "Display this help information")

    console.print("\n")
    console.print(
        Panel(
            commands_table,
            title="[bold yellow]📋 Available Commands[/bold yellow]",
            border_style="yellow",
        )
    )

    # Create examples table
    examples_table = Table(show_header=True, header_style="bold green")
    examples_table.add_column("Example", style="bright_green", width=35)
    examples_table.add_column("Description", width=45)

    examples_table.add_row(
        "sre-agent diagnose frontend", "Diagnose issues with the 'frontend' service"
    )
    examples_table.add_row(
        "sre-agent diagnose cartservice", "Analyse problems with the 'cartservice'"
    )
    examples_table.add_row("sre-agent config", "Configure Slack, LLM Firewall, AWS cluster, etc.")

    console.print("\n")
    console.print(
        Panel(
            examples_table,
            title="[bold green]💡 Usage Examples[/bold green]",
            border_style="green",
        )
    )

    console.print(
        "\n[dim]💡 First time using SRE Agent? The setup wizard will guide you through "
        "configuration automatically![/dim]"
    )
