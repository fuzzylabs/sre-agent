"""CLI banner rendering."""

from importlib.metadata import PackageNotFoundError, version

from rich.panel import Panel
from rich.text import Text

from sre_agent.cli.ascii_art import get_ascii_art
from sre_agent.cli.ui import console


def print_global_banner() -> None:
    """Print the main CLI banner."""
    ascii_art = get_ascii_art().strip("\n")
    banner_text = Text()
    colours = ["orange1", "dark_orange", "orange3", "orange1"]
    banner_text.append("\n")
    for index, line in enumerate(ascii_art.splitlines()):
        if not line.strip():
            banner_text.append("\n")
            continue
        banner_text.append(f"{line}\n", style=colours[index % len(colours)])

    banner_text.append(
        "\nYour AI-powered Site Reliability Engineering assistant\n",
        style="bright_white",
    )
    banner_text.append("Diagnose • Monitor • Debug • Scale\n", style="dim white")
    banner_text.append(f"v{_get_version()}\n", style="orange1")
    console.print(
        Panel(
            banner_text,
            title="Welcome to SRE Agent",
            border_style="cyan",
        )
    )


def _get_version() -> str:
    """Return the CLI version.

    Returns:
        The CLI version string.
    """
    try:
        return version("sre-agent")
    except PackageNotFoundError:
        return "0.2.0"
