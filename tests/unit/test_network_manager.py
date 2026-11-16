"""Tests for Network Manager diagnostics."""

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from devnaro import network_manager


def completed(args, returncode=0, stdout="", stderr=""):
    return CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_process_status_returns_running_process(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[0] == "pgrep":
            return completed(args, stdout="123\n")
        if args[0] == "ps":
            return completed(
                args,
                stdout="123 1 devuser S 00:12 python3 -u /opt/network-manager/manager.py\n",
            )
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr(network_manager.subprocess, "run", fake_run)

    running, processes = network_manager.process_status()

    assert running is True
    assert len(processes) == 1
    process = processes[0]
    assert process.pid == 123
    assert process.ppid == 1
    assert process.user == "devuser"
    assert process.state == "S"
    assert process.elapsed == "00:12"
    assert "manager.py" in process.command
    assert [call[0] for call in calls] == ["pgrep", "ps"]


def test_process_status_returns_not_running(monkeypatch):
    def fake_run(args, **kwargs):
        return completed(args, returncode=1)

    monkeypatch.setattr(network_manager.subprocess, "run", fake_run)

    running, details = network_manager.process_status()

    assert running is False
    assert details == "No matching process found."


def test_process_status_handles_missing_pgrep(monkeypatch):
    def fake_run(args, **kwargs):
        if args[0] == "pgrep":
            raise FileNotFoundError
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr(network_manager.subprocess, "run", fake_run)

    running, details = network_manager.process_status()

    assert running is False
    assert "procps" in details


def test_process_status_handles_missing_ps(monkeypatch):
    def fake_run(args, **kwargs):
        if args[0] == "pgrep":
            return completed(args, stdout="123\n")
        raise FileNotFoundError

    monkeypatch.setattr(network_manager.subprocess, "run", fake_run)

    running, details = network_manager.process_status()

    assert running is False
    assert details == "ps is not installed (install the procps package)."


def test_process_status_handles_process_disappearing(monkeypatch):
    def fake_run(args, **kwargs):
        if args[0] == "pgrep":
            return completed(args, stdout="123\n")
        return completed(args, returncode=1)

    monkeypatch.setattr(network_manager.subprocess, "run", fake_run)

    running, details = network_manager.process_status()

    assert running is False
    assert details == "Process disappeared before its details could be read."


def test_read_logs_returns_last_lines(tmp_path: Path):
    log_file = tmp_path / "manager.log"
    log_file.write_text("one\ntwo\nthree\n", encoding="utf-8")

    result = network_manager.read_logs(lines=2, path=log_file)

    assert result == "two\nthree"


def test_read_logs_rejects_zero_lines(tmp_path: Path):
    log_file = tmp_path / "manager.log"
    log_file.write_text("one\n", encoding="utf-8")

    with pytest.raises(ValueError, match="greater than zero"):
        network_manager.read_logs(lines=0, path=log_file)


def test_read_logs_reports_missing_file(tmp_path: Path):
    missing_file = tmp_path / "missing.log"

    with pytest.raises(FileNotFoundError, match="Network Manager log not found"):
        network_manager.read_logs(path=missing_file)
