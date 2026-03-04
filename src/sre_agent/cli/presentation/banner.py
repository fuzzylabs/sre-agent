"""CLI banner rendering."""

import time
from importlib.metadata import PackageNotFoundError, version

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from sre_agent.cli.presentation.ascii_art import get_ascii_art
from sre_agent.cli.presentation.console import console

_COLOURS = ["#A78BFA", "#818CF8", "#67E8F9", "#5EEAD4"]
_ANIMATION_FRAMES = 12
_FRAME_DELAY = 0.1


def print_global_banner(animated: bool = True) -> None:
    """Print the main CLI banner."""
    if animated:
        _print_animated_banner()
    else:
        console.print(_build_banner(colour_offset=0))


def _print_animated_banner() -> None:
    """Play a colour-wave animation then print the final static banner."""
    with Live(
        _build_banner(colour_offset=0),
        console=console,
        refresh_per_second=20,
        transient=True,
    ) as live:
        for frame in range(_ANIMATION_FRAMES):
            live.update(_build_banner(colour_offset=frame))
            time.sleep(_FRAME_DELAY)
    console.print(_build_banner(colour_offset=_ANIMATION_FRAMES))


def _build_banner(colour_offset: int) -> Panel:
    """Build the banner panel with a shifted colour palette."""
    ascii_art = get_ascii_art().strip("\n")
    # spellchecker:ignore-next-line
    banner_text = Text(justify="center")
    banner_text.append("\n")
    for index, line in enumerate(ascii_art.splitlines()):
        if not line.strip():
            banner_text.append("\n")
            continue
        colour = _COLOURS[(index + colour_offset) % len(_COLOURS)]
        banner_text.append(f"{line}\n", style=colour)

    banner_text.append(
        "\n🤖 Your AI-powered Site Reliability Engineering assistant\n",
        style="bright_white",
    )
    banner_text.append("Diagnose • Monitor • Debug • Scale\n", style="dim white")
    banner_text.append("\n")

    footer_text = Text(justify="right")
    footer_text.append(f"v{_get_version()}\n", style="#5EEAD4")
    footer_text.append("Made by Fuzzy Labs", style="dim white")
    return Panel(
        Group(banner_text, footer_text),
        title="Welcome to SRE Agent",
        border_style="#5EEAD4",
        expand=True,
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
