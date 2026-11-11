"""Shared Rich presentation helpers for a consistent DevBox CLI."""

from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme


DEVBOX_STYLE_STRINGS = {
    "info": "bright_cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "muted": "dim",
    "heading": "bold bright_cyan",
    "accent": "bold green",
    "value": "white",
}
DEVBOX_THEME = Theme(DEVBOX_STYLE_STRINGS)


def configure_typer_help() -> None:
    """Align Typer's built-in help renderer with the DevBox color palette."""
    from typer import rich_utils

    styles = {
        "STYLE_USAGE": DEVBOX_STYLE_STRINGS["heading"],
        "STYLE_USAGE_COMMAND": "bold",
        "STYLE_OPTION": DEVBOX_STYLE_STRINGS["heading"],
        "STYLE_SWITCH": DEVBOX_STYLE_STRINGS["heading"],
        "STYLE_NEGATIVE_OPTION": DEVBOX_STYLE_STRINGS["heading"],
        "STYLE_NEGATIVE_SWITCH": DEVBOX_STYLE_STRINGS["heading"],
        "STYLE_OPTIONS_PANEL_BORDER": DEVBOX_STYLE_STRINGS["info"],
        "STYLE_COMMANDS_PANEL_BORDER": DEVBOX_STYLE_STRINGS["info"],
        "STYLE_ERRORS_PANEL_BORDER": DEVBOX_STYLE_STRINGS["error"],
        "STYLE_COMMANDS_TABLE_FIRST_COLUMN": DEVBOX_STYLE_STRINGS["heading"],
        "STYLE_HELPTEXT": DEVBOX_STYLE_STRINGS["value"],
        "STYLE_OPTION_HELP": DEVBOX_STYLE_STRINGS["value"],
    }

    for name, style in styles.items():
        if hasattr(rich_utils, name):
            setattr(rich_utils, name, style)


def render_panel(
    console: Console,
    title: str,
    content: Any,
    *,
    border_style: str = "info",
    subtitle: str | None = None,
    padding: tuple[int, int] = (1, 1),
) -> None:
    """Render command output inside the standard DevBox panel."""
    console.print(
        Panel(
            content,
            title=f"[heading]{title}[/heading]",
            subtitle=subtitle,
            border_style=border_style,
            box=box.ROUNDED,
            padding=padding,
            expand=False,
        )
    )
