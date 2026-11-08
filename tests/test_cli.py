"""Smoke tests for the DevBox command line interface."""

from typer.testing import CliRunner

from devbox_manager import __version__
from devbox_manager.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Inspect and troubleshoot your DevBox environment" in result.stdout


def test_cli_version():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_network_manager_help():
    result = runner.invoke(app, ["network-manager", "--help"])

    assert result.exit_code == 0
    assert "Inspect the automatic Docker network manager" in result.stdout
