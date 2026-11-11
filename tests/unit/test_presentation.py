"""Tests for the shared CLI presentation template."""

from io import StringIO

from rich.console import Console

from devbox_manager.presentation import render_panel


def test_render_panel_uses_consistent_framed_layout():
    output = StringIO()
    console = Console(file=output, width=80, force_terminal=False, color_system=None)

    render_panel(
        console,
        "Example command",
        "Command output",
        subtitle="1 item found",
    )

    rendered = output.getvalue()
    assert "Example command" in rendered
    assert "Command output" in rendered
    assert "1 item found" in rendered
    assert "╭" in rendered
    assert "╰" in rendered


def test_typer_help_uses_devbox_theme():
    from typer import rich_utils

    from devbox_manager.presentation import configure_typer_help

    configure_typer_help()

    assert rich_utils.STYLE_USAGE == "bold bright_cyan"
    assert rich_utils.STYLE_OPTIONS_PANEL_BORDER == "bright_cyan"
    assert rich_utils.STYLE_COMMANDS_PANEL_BORDER == "bright_cyan"
    assert rich_utils.STYLE_COMMANDS_TABLE_FIRST_COLUMN == "bold bright_cyan"
