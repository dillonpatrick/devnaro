"""Smoke tests for the DevBox command line interface."""

from typer.testing import CliRunner

from devbox_manager import __version__
from devbox_manager.cli import app

runner = CliRunner()



def test_info_shows_stack_base_and_tool_sources(monkeypatch, tmp_path):
    from devbox_manager import cli

    user_bin = tmp_path / ".local" / "bin"
    user_bin.mkdir(parents=True)
    user_tool = user_bin / "custom-tool"
    user_tool.write_text("#!/bin/sh\necho custom-tool 2.4.0\n", encoding="utf-8")
    user_tool.chmod(0o755)

    sdk_bin = tmp_path / "sdk" / "bin"
    sdk_bin.mkdir(parents=True)
    sdk_tool = sdk_bin / "custom-sdk"
    sdk_tool.write_text("#!/bin/sh\necho custom-sdk 5.1.0\n", encoding="utf-8")
    sdk_tool.chmod(0o755)

    monkeypatch.setenv("PATH", f"{user_bin}:{sdk_bin}:/usr/bin")
    monkeypatch.setattr(cli.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(cli.Path, "read_text", lambda self, **kwargs: "3.22.0")
    monkeypatch.setattr(
        cli.shutil,
        "which",
        lambda executable: f"/usr/bin/{executable}",
    )
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "DevBox info" in result.stdout
    assert "Stack" in result.stdout
    assert "Alpine Linux" in result.stdout
    assert "Terraform" in result.stdout
    assert "Docker Compose" in result.stdout
    assert "Path" in result.stdout
    assert "/usr/bin/terraform" in result.stdout
    assert "Image" in result.stdout
    assert "custom-tool" in result.stdout
    assert "custom-sdk" in result.stdout
    assert "Custom PATH" in result.stdout
    assert "sdk/bin/custom-sdk" in result.stdout
    assert ".local/bin/custom-tool" in result.stdout
    assert result.stdout.index("Custom PATH") < result.stdout.index("Image") < result.stdout.index("User")
    assert "User" in result.stdout
    assert "Docker Engine" in result.stdout
    assert "VS Code bridge" in result.stdout

def test_cli_help():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Inspect and troubleshoot your DevBox environment" in result.stdout
    assert "--install-completion" not in result.stdout
    assert "--show-completion" not in result.stdout


def test_cli_short_help():
    result = runner.invoke(app, ["-h"])

    assert result.exit_code == 0
    assert "Inspect and troubleshoot your DevBox environment" in result.stdout


def test_network_manager_short_help():
    result = runner.invoke(app, ["network-manager", "-h"])

    assert result.exit_code == 0
    assert "Inspect the automatic Docker network manager" in result.stdout


def test_welcome_separates_host_and_container_quick_commands(monkeypatch):
    from devbox_manager import cli

    monkeypatch.setattr(cli, "process_status", lambda: (True, "Network Manager running"))
    result = runner.invoke(app, ["welcome"])

    assert result.exit_code == 0
    assert "QUICK COMMANDS" in result.stdout
    assert "INSIDE CONTAINER" in result.stdout
    assert "HOST COMMANDS" not in result.stdout
    assert "OUTSIDE CONTAINER" not in result.stdout
    assert "Host commands:" not in result.stdout
    assert "devbox info" not in result.stdout
    assert "dm info" in result.stdout
    assert "dm tools search QUERY" in result.stdout
    assert "dm status" in result.stdout
    assert "dm doctor" in result.stdout
    assert "dm networks" in result.stdout
    assert "dm network-manager status" in result.stdout
    assert "dm network-manager logs" in result.stdout
    assert "docker ps" in result.stdout
    assert "docker compose up -d" in result.stdout
    assert max(map(len, result.stdout.splitlines())) <= 80


def test_welcome_commands_come_from_registered_typer_tree():
    from devbox_manager.cli import _registered_cli_commands

    commands = dict(_registered_cli_commands())

    assert "dm info" in commands
    assert "dm network-manager status" in commands
    assert "dm network-manager logs" in commands
    assert "dm tools search QUERY" in commands
    assert all("__complete" not in usage for usage in commands)
    assert "Search official Alpine Linux repositories for available packages." in commands[
        "dm tools search QUERY"
    ]


def test_completion_candidates_follow_registered_command_tree():
    from devbox_manager.cli import _completion_candidates

    assert "tools" in _completion_candidates([""])
    assert _completion_candidates(["tools", ""]) == ["search"]
    assert _completion_candidates(["network-manager", ""]) == ["logs", "status"]


def test_hidden_completion_command_returns_candidates():
    result = runner.invoke(app, ["__complete", "--", "tools", ""])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["search"]


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



def test_network_manager_status_shows_explained_process_details(monkeypatch):
    from devbox_manager import cli
    from devbox_manager.network_manager import NetworkManagerProcess

    process = NetworkManagerProcess(
        pid=27,
        ppid=1,
        user="root",
        state="S",
        elapsed="00:12",
        command="python3 -u /opt/network-manager/manager.py",
    )
    monkeypatch.setattr(cli, "process_status", lambda: (True, [process]))

    result = runner.invoke(app, ["network-manager", "status"])

    assert result.exit_code == 0
    assert "PID" in result.stdout
    assert "PPID" in result.stdout
    assert "Uptime" in result.stdout
    assert "27" in result.stdout
    assert "00:12" in result.stdout
    assert "Process ID (PID)" in result.stdout



def test_tools_search_queries_external_alpine_packages(monkeypatch):
    from devbox_manager import cli
    from devbox_manager.alpine_packages import AlpinePackage

    monkeypatch.setattr(
        cli,
        "search_alpine_packages",
        lambda query: (
            AlpinePackage(
                name="terraform",
                version="1.9.8-r0",
                description="Infrastructure as Code tool",
                repository="community",
                architecture="x86_64",
                alpine_version="3.22",
            ),
        ),
    )
    result = runner.invoke(app, ["tools", "search", "terraform"])

    assert result.exit_code == 0
    assert "Alpine package search" in result.stdout
    assert "terraform" in result.stdout
    assert "1.9.8-r0" in result.stdout
    assert "community" in result.stdout


def test_tools_search_reports_no_external_matches(monkeypatch):
    from devbox_manager import cli

    monkeypatch.setattr(cli, "search_alpine_packages", lambda query: ())
    result = runner.invoke(app, ["tools", "search", "no-such-tool"])

    assert result.exit_code == 0
    assert "No matching Alpine packages found" in result.stdout


def test_tools_search_reports_network_errors(monkeypatch):
    from devbox_manager import cli
    from devbox_manager.alpine_packages import AlpinePackageSearchError

    def fail_search(query):
        raise AlpinePackageSearchError("repository unavailable")

    monkeypatch.setattr(cli, "search_alpine_packages", fail_search)
    result = runner.invoke(app, ["tools", "search", "terraform"])

    assert result.exit_code == 1
    assert "repository unavailable" in result.stdout


def test_tools_help_lists_only_external_search():
    result = runner.invoke(app, ["tools", "--help"])

    assert result.exit_code == 0
    assert "search" in result.stdout
    assert "list" not in result.stdout


def test_tools_list_is_not_available():
    result = runner.invoke(app, ["tools", "list"])

    assert result.exit_code != 0
    assert "No such command" in result.output
