"""CLI entrypoint for the SRE Agent."""

import click

from sre_agent.cli.interactive_shell import start_interactive_shell


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Run the SRE Agent CLI entrypoint.

    Args:
        ctx: Click context for the command invocation.
    """
    if ctx.invoked_subcommand is None:
        start_interactive_shell()


def main() -> None:
    """Run the CLI."""
    cli()
