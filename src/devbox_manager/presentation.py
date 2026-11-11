"""Shared Rich presentation helpers for a consistent DevBox CLI."""

from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel


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
