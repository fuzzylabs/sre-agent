"""Interactive shell for guided deployment."""

import questionary

from sre_agent.cli.configuration import ensure_required_config
from sre_agent.cli.mode.local import run_local_mode
from sre_agent.cli.mode.remote.menu import run_remote_mode
from sre_agent.cli.presentation.banner import print_global_banner
from sre_agent.cli.presentation.console import console


def _refresh_screen(message: str = "") -> None:
    """Clear the screen and reprint the banner with an optional status message."""
    console.clear()
    print_global_banner(animated=False)
    if message:
        console.print(message)


def start_interactive_shell() -> None:
    """Start the interactive deployment shell."""
    print_global_banner()
    ensure_required_config()

    _refresh_screen()
    while True:
        choice = questionary.select(
            "Running Mode:",
            choices=[
                "Local",
                "Remote Deployment",
                "Exit",
            ],
        ).ask()

        if choice in (None, "Exit"):
            console.print("Goodbye.")
            return

        if choice == "Local":
            run_local_mode()
        elif choice == "Remote Deployment":
            run_remote_mode()

        _refresh_screen()
