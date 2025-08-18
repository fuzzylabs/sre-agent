"""Interactive mode for SRE Agent CLI."""

import asyncio
from typing import Any, Optional

import click
import httpx
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.spinner import Spinner
from rich.table import Table

from ..utils.config import SREAgentConfig

console = Console()


class InteractiveSession:
    """Interactive debugging session with the SRE Agent."""

    def __init__(
        self, config: SREAgentConfig, cluster: Optional[str] = None, namespace: str = "default"
    ) -> None:
        """Initialise the interactive session.

        Args:
            config: The SRE Agent configuration object.
            cluster: The Kubernetes cluster name. Defaults to None.
            namespace: The Kubernetes namespace. Defaults to "default".
        """
        self.config = config
        self.cluster = cluster
        self.namespace = namespace
        self.session_history: list[dict[str, Any]] = []
        self.context: dict[str, Any] = {}

    def _handle_special_commands(self, user_input: str) -> bool:
        """Handle special commands and return True if command was handled."""
        cmd = user_input.lower()
        handled = True

        if cmd in ["quit", "exit", "q"]:
            if Confirm.ask("Are you sure you want to exit?"):
                console.print("[yellow]Goodbye! 👋[/yellow]")
                return True  # we really do want to exit here
            handled = False

        elif cmd == "help":
            self._show_help()

        elif cmd == "clear":
            console.clear()

        elif cmd == "history":
            self._show_history()

        elif cmd == "context":
            self._show_context()

        elif cmd.startswith("set "):
            self._handle_set_command(user_input[4:])

        else:
            handled = False

        return handled

    def _get_user_input(self) -> str:
        """Get and validate user input."""
        try:
            user_input = Prompt.ask("\n[bold cyan]sre-agent>[/bold cyan]", default="").strip()
            return user_input
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'quit' or 'exit' to leave the session.[/yellow]")
            return ""
        except EOFError:
            console.print("\n[yellow]Session ended.[/yellow]")
            return "EOF"

    async def start(self) -> None:
        """Start the interactive session."""
        console.print(
            Panel(
                "[bold cyan]🤖 SRE Agent Interactive Mode[/bold cyan]\n\n"
                "Welcome to interactive debugging! I'm your AI-powered SRE assistant.\n"
                "I can help you diagnose issues, analyse logs, and troubleshoot problems.\n\n"
                "[dim]Type 'help' for commands, 'quit' or 'exit' to leave.[/dim]",
                border_style="cyan",
                title="Interactive Session Started",
            )
        )

        # Show current context
        self._show_context()

        while True:
            # Get user input
            user_input = self._get_user_input()

            # Handle EOF (end of file/input)
            if user_input == "EOF":
                break

            # Skip empty input
            if not user_input:
                continue

            # Handle special commands
            if self._handle_special_commands(user_input):
                break  # Exit session

            # Process regular query
            await self._process_query(user_input)

    def _show_help(self) -> None:
        """Show help information."""
        help_table = Table(show_header=True, header_style="bold cyan")
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description")

        help_table.add_row("help", "Show this help message")
        help_table.add_row("quit, exit, q", "Exit the interactive session")
        help_table.add_row("clear", "Clear the screen")
        help_table.add_row("history", "Show conversation history")
        help_table.add_row("context", "Show current session context")
        help_table.add_row("set <key>=<value>", "Set context variables (e.g., set service=myapp)")
        help_table.add_row("", "")
        help_table.add_row("[bold]Natural language queries:[/bold]", "")
        help_table.add_row("", "• What's wrong with my service?")
        help_table.add_row("", "• Check logs for myapp")
        help_table.add_row("", "• Why is my pod crashing?")
        help_table.add_row("", "• Analyse recent errors")

        console.print(
            Panel(
                help_table,
                title="[bold cyan]Interactive Commands[/bold cyan]",
                border_style="cyan",
            )
        )

    def _show_history(self) -> None:
        """Show conversation history."""
        if not self.session_history:
            console.print("[dim]No conversation history yet.[/dim]")
            return

        console.print(
            Panel(
                "\n".join(
                    [
                        f"[bold cyan]User:[/bold cyan] {entry['query']}\n"
                        f"[bold green]Agent:[/bold green] {entry['response'][:200]}"
                        f"{'...' if len(entry['response']) > 200 else ''}\n"  # noqa: PLR2004
                        for entry in self.session_history[-5:]  # Show last 5 entries
                    ]
                ),
                title="[bold cyan]Recent History[/bold cyan]",
                border_style="cyan",
            )
        )

    def _show_context(self) -> None:
        """Show current session context."""
        context_table = Table(show_header=False, box=None, padding=(0, 1))
        context_table.add_row("[cyan]Cluster:[/cyan]", self.cluster or "[dim]Not set[/dim]")
        context_table.add_row("[cyan]Namespace:[/cyan]", self.namespace)

        for key, value in self.context.items():
            context_table.add_row(f"[cyan]{key}:[/cyan]", str(value))

        console.print(
            Panel(
                context_table,
                title="[bold cyan]Session Context[/bold cyan]",
                border_style="cyan",
            )
        )

    def _handle_set_command(self, command: str) -> None:
        """Handle set commands to update context."""
        try:
            if "=" not in command:
                console.print("[red]Invalid set command. Use: set key=value[/red]")
                return

            key, value = command.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Handle special context keys
            if key == "cluster":
                self.cluster = value if value else None
            elif key == "namespace":
                self.namespace = value or "default"
            else:
                self.context[key] = value

            console.print(f"[green]Set {key} = {value}[/green]")

        except Exception as e:
            console.print(f"[red]Error setting context: {e}[/red]")

    async def _process_query(self, query: str) -> None:
        """Process a user query."""
        # Add query to history
        history_entry: dict[str, str] = {"query": query, "response": ""}

        # Prepare the request
        payload: dict[str, Any] = {
            "text": query,
            "context": {
                "cluster": self.cluster,
                "namespace": self.namespace,
                **self.context,
            },
            "interactive": True,
        }

        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.config.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.config.api_url.rstrip('/')}/diagnose"

        # Show thinking indicator
        with Live(
            Spinner("dots", text="🤔 Thinking..."),
            console=console,
            refresh_per_second=10,
        ):
            try:
                async with httpx.AsyncClient(timeout=self.config.default_timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 200:  # noqa: PLR2004
                    result = response.json()
                    response_text = self._format_response(result)
                    history_entry["response"] = response_text

                    console.print(
                        Panel(
                            Markdown(response_text),
                            title="[bold green]🤖 SRE Agent Response[/bold green]",
                            border_style="green",
                        )
                    )

                elif response.status_code == 401:  # noqa: PLR2004
                    console.print("[red]Authentication failed. Check your bearer token.[/red]")
                    return
                elif response.status_code == 404:  # noqa: PLR2004
                    console.print(
                        "[red]API endpoint not found. Make sure SRE Agent is running.[/red]"
                    )
                    return
                else:
                    console.print(f"[red]Request failed with status {response.status_code}[/red]")
                    if response.text:
                        console.print(f"[red]{response.text}[/red]")
                    return

            except httpx.TimeoutException:
                console.print(
                    f"[red]Request timed out after {self.config.default_timeout} seconds[/red]"
                )
                return
            except httpx.ConnectError:
                console.print(
                    f"[red]Failed to connect to SRE Agent API at {self.config.api_url}[/red]"
                )
                console.print("[yellow]Make sure the SRE Agent services are running[/yellow]")
                return
            except Exception as e:
                console.print(f"[red]Unexpected error: {e}[/red]")
                return

        # Add to history
        self.session_history.append(history_entry)

    def _format_response(self, result: dict[str, Any]) -> str:
        """Format the API response for display."""
        if "error" in result:
            return f"❌ **Error**: {result['error']}"

        response_parts: list[str] = []

        if "diagnosis" in result:
            response_parts.append(f"## 🔍 Diagnosis\n\n{result['diagnosis']}")

        if "details" in result and result["details"]:
            response_parts.append("## 📊 Component Analysis")
            for detail in result["details"]:
                status_emoji = "✅" if detail.get("status") == "healthy" else "❌"
                response_parts.append(
                    f"- **{detail.get('component', 'Unknown')}**: {status_emoji} "
                    f"{detail.get('status', 'Unknown')} - {detail.get('message', '')}"
                )

        if "recommendations" in result and result["recommendations"]:
            response_parts.append("## 💡 Recommendations")
            for rec in result["recommendations"]:
                response_parts.append(f"- {rec}")

        if "logs" in result and result["logs"]:
            response_parts.append("## 📝 Relevant Logs")
            response_parts.append(
                f"```\n{result['logs'][:1000]}{'...' if len(result['logs']) > 1000 else ''}\n```"  # noqa: PLR2004
            )

        return (
            "\n\n".join(response_parts) if response_parts else "No specific information available."
        )


@click.command()
@click.option("--cluster", "-c", help="Kubernetes cluster name")
@click.option("--namespace", "-n", help="Kubernetes namespace")
@click.pass_context
def interactive(ctx: click.Context, cluster: Optional[str], namespace: Optional[str]) -> None:
    """Start an interactive debugging session with the SRE Agent.

    In interactive mode, you can have a conversation with the AI assistant
    to diagnose issues, analyse logs, and get recommendations for your
    infrastructure problems.

    Examples:
      # Start interactive session
      sre-agent interactive

      # Start with specific cluster context
      sre-agent interactive --cluster prod --namespace production

    Once in interactive mode, you can ask questions like:
    - "What's wrong with my service?"
    - "Check logs for myapp"
    - "Why is my pod crashing?"
    - "Analyse recent errors"
    """
    try:
        config = ctx.obj["config"]
    except (KeyError, TypeError):
        console.print("[red]Configuration not loaded. Run 'sre-agent config setup' first.[/red]")
        return

    # Validate required configuration
    if not config.bearer_token:
        console.print("[red]Bearer token not configured. Run 'sre-agent config setup' first.[/red]")
        return

    if not config.api_url:
        console.print("[red]API URL not configured. Run 'sre-agent config setup' first.[/red]")
        return

    # Use command-line options or fall back to config defaults
    cluster = cluster or config.default_cluster
    namespace = namespace or config.default_namespace

    # Start interactive session
    session = InteractiveSession(config, cluster, namespace)
    asyncio.run(session.start())
