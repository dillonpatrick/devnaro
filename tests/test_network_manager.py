"""Tests for Network Manager diagnostics."""

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from devbox_manager import network_manager


def test_process_status_returns_running_process(monkeypatch):
    def fake_run(*args, **kwargs):
        return CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="123 python3 /opt/network-manager/manager.py",
            stderr="",
        )

    monkeypatch.setattr(network_manager.subprocess, "run", fake_run)

    running, details = network_manager.process_status()

    assert running is True
    assert "manager.py" in details


def test_process_status_returns_not_running(monkeypatch):
    def fake_run(*args, **kwargs):
        return CompletedProcess(args=args[0], returncode=1, stdout="", stderr="")

    monkeypatch.setattr(network_manager.subprocess, "run", fake_run)

    running, details = network_manager.process_status()

    assert running is False
    assert details == ""


def test_process_status_handles_missing_pgrep(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(network_manager.subprocess, "run", fake_run)

    running, details = network_manager.process_status()

    assert running is False
    assert "procps" in details


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
