"""Shared Rich console for the CLI."""

import questionary
import questionary.constants as questionary_constants
import questionary.styles as questionary_styles
from rich.console import Console

console = Console()

QUESTIONARY_STYLE = questionary.Style(
    [
        ("qmark", "fg:#5f819d"),
        ("question", "fg:#e0e0e0 bold"),
        ("answer", "fg:#FF9D00 bold"),
        ("search_success", "noinherit fg:#00FF00 bold"),
        ("search_none", "noinherit fg:#FF0000 bold"),
        ("pointer", "fg:#e0e0e0"),
        ("highlighted", "fg:#f2f2f2"),
        ("selected", "fg:#e0e0e0"),
        ("separator", "fg:#e0e0e0"),
        ("instruction", "fg:#e0e0e0"),
        ("text", "fg:#e0e0e0"),
        ("disabled", "fg:#bdbdbd italic"),
    ]
)

# Use the CLI palette as the default Questionary style for all prompts.
questionary_constants.DEFAULT_STYLE = QUESTIONARY_STYLE
setattr(questionary_styles, "DEFAULT_STYLE", QUESTIONARY_STYLE)
