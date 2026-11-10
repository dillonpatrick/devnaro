"""Smoke tests for the DevBox command line interface."""

from typer.testing import CliRunner

from devbox_manager import __version__
from devbox_manager.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Inspect and troubleshoot your DevBox environment" in result.stdout
    assert "--install-completion" not in result.stdout
    assert "--show-completion" not in result.stdout


def test_cli_version():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_short_version():
    result = runner.invoke(app, ["-v"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_network_manager_help():
    result = runner.invoke(app, ["network-manager", "--help"])

    assert result.exit_code == 0
    assert "Inspect the automatic Docker network manager" in result.stdout


def test_format_started_at_accepts_docker_nanoseconds():
    from devbox_manager.cli import _format_started_at

    result = _format_started_at("2026-11-08T13:42:43.711548725+00:00")

    assert result.startswith("2026-11-08 13:42:43")


def test_format_started_at_handles_zero_timestamp():
    from devbox_manager.cli import _format_started_at

    assert _format_started_at("0001-01-01T00:00:00Z") == "Not running"

