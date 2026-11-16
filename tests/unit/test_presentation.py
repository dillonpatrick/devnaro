"""Tests for the shared CLI presentation template."""

from io import StringIO

from rich.console import Console

from devnaro.presentation import render_panel


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


def test_typer_help_uses_devnaro_theme():
    from typer import rich_utils

    from devnaro.presentation import configure_typer_help

    configure_typer_help()

    assert rich_utils.STYLE_USAGE == "bold bright_cyan"
    assert rich_utils.STYLE_OPTIONS_PANEL_BORDER == "bright_cyan"
    assert rich_utils.STYLE_COMMANDS_PANEL_BORDER == "bright_cyan"
    assert rich_utils.STYLE_COMMANDS_TABLE_FIRST_COLUMN == "bold bright_cyan"
    assert rich_utils.MAX_WIDTH == 88



def test_devnaro_theme_uses_named_semantic_palette():
    from devnaro.presentation import DEVNARO_THEME

    assert DEVNARO_THEME.styles["info"].color.name == "bright_cyan"
    assert DEVNARO_THEME.styles["heading"].color.name == "bright_cyan"
    assert DEVNARO_THEME.styles["success"].color.name == "green"
    assert DEVNARO_THEME.styles["warning"].color.name == "yellow"
    assert DEVNARO_THEME.styles["error"].color.name == "red"
    assert DEVNARO_THEME.styles["value"].color.name == "white"



def test_render_panel_fits_content_instead_of_terminal_width():
    output = StringIO()
    console = Console(file=output, width=100, force_terminal=False, color_system=None)

    render_panel(console, "Compact panel", "Short output")

    rendered_lines = output.getvalue().splitlines()
    assert max(map(len, rendered_lines)) < 100
