"""Interactive shell for guided deployment."""

import questionary

from sre_agent.cli.configuration import ensure_required_config
from sre_agent.cli.mode.local import run_local_mode
from sre_agent.cli.mode.remote.menu import run_remote_mode
from sre_agent.cli.presentation.banner import print_global_banner
from sre_agent.cli.presentation.console import console


def start_interactive_shell() -> None:
    """Start the interactive deployment shell."""
    print_global_banner()
    ensure_required_config()

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
