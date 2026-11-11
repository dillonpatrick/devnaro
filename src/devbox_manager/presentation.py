"""Shared Rich presentation helpers for a consistent DevBox CLI."""

from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel


def configure_typer_help() -> None:
    """Align Typer's built-in help renderer with the DevBox color palette."""
    from typer import rich_utils

    styles = {
        "STYLE_USAGE": "bold bright_cyan",
        "STYLE_USAGE_COMMAND": "bold",
        "STYLE_OPTION": "bold bright_cyan",
        "STYLE_SWITCH": "bold bright_cyan",
        "STYLE_NEGATIVE_OPTION": "bold bright_cyan",
        "STYLE_NEGATIVE_SWITCH": "bold bright_cyan",
        "STYLE_OPTIONS_PANEL_BORDER": "bright_cyan",
        "STYLE_COMMANDS_PANEL_BORDER": "bright_cyan",
        "STYLE_ERRORS_PANEL_BORDER": "red",
        "STYLE_COMMANDS_TABLE_FIRST_COLUMN": "bold bright_cyan",
        "STYLE_HELPTEXT": "white",
        "STYLE_OPTION_HELP": "white",
    }

    for name, style in styles.items():
        if hasattr(rich_utils, name):
            setattr(rich_utils, name, style)


def render_panel(
    console: Console,
    title: str,
    content: Any,
    *,
    border_style: str = "bright_cyan",
    subtitle: str | None = None,
    padding: tuple[int, int] = (1, 1),
    expand: bool = False,
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
            expand=expand,
        )
    )
