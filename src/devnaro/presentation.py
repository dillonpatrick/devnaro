"""Shared Rich presentation helpers for a consistent DevNaro CLI."""

from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme


DEVNARO_STYLE_STRINGS = {
    "info": "bright_cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "muted": "dim",
    "heading": "bold bright_cyan",
    "accent": "bold green",
    "value": "white",
}
DEVNARO_THEME = Theme(DEVNARO_STYLE_STRINGS)


def configure_typer_help() -> None:
    """Align Typer's built-in help renderer with the DevNaro color palette."""
    from typer import rich_utils

    # Typer renders help panels with an expanding table. Cap its Rich console width
    # so the panels do not stretch across unusually wide terminals.
    if hasattr(rich_utils, "MAX_WIDTH"):
        rich_utils.MAX_WIDTH = min(rich_utils.MAX_WIDTH or 88, 88)

    styles = {
        "STYLE_USAGE": DEVNARO_STYLE_STRINGS["heading"],
        "STYLE_USAGE_COMMAND": "bold",
        "STYLE_OPTION": DEVNARO_STYLE_STRINGS["heading"],
        "STYLE_SWITCH": DEVNARO_STYLE_STRINGS["heading"],
        "STYLE_NEGATIVE_OPTION": DEVNARO_STYLE_STRINGS["heading"],
        "STYLE_NEGATIVE_SWITCH": DEVNARO_STYLE_STRINGS["heading"],
        "STYLE_OPTIONS_PANEL_BORDER": DEVNARO_STYLE_STRINGS["info"],
        "STYLE_COMMANDS_PANEL_BORDER": DEVNARO_STYLE_STRINGS["info"],
        "STYLE_ERRORS_PANEL_BORDER": DEVNARO_STYLE_STRINGS["error"],
        "STYLE_COMMANDS_TABLE_FIRST_COLUMN": DEVNARO_STYLE_STRINGS["heading"],
        "STYLE_HELPTEXT": DEVNARO_STYLE_STRINGS["value"],
        "STYLE_OPTION_HELP": DEVNARO_STYLE_STRINGS["value"],
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
    """Render command output inside the standard DevNaro panel."""
    with console.use_theme(DEVNARO_THEME):
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
