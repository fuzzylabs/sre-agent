"""Remote deployment mode for the CLI."""

import questionary

from sre_agent.cli.mode.remote.aws.ecs.menu import run_aws_ecs_mode


def run_remote_mode() -> None:
    """Run the remote deployment actions."""
    target = questionary.select(
        "Remote Deployment:",
        choices=[
            "AWS ECS",
            "Back",
        ],
    ).ask()

    if target in (None, "Back"):
        return
    if target == "AWS ECS":
        run_aws_ecs_mode()
