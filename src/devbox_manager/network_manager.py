"""Helpers for inspecting the Network Manager process and logs."""

import subprocess
from collections import deque
from pathlib import Path

from devbox_manager.config import NETWORK_MANAGER_LOG, NETWORK_MANAGER_PROCESS


def process_status() -> tuple[bool, str]:
    """Return whether the Network Manager process is running."""
    process_pattern = f"[{NETWORK_MANAGER_PROCESS[0]}]{NETWORK_MANAGER_PROCESS[1:]}"

    try:
        result = subprocess.run(
            ["pgrep", "-af", process_pattern],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "pgrep is not installed (install the procps package)."

    return result.returncode == 0, result.stdout.strip() or result.stderr.strip()


def read_logs(lines: int = 50, path: Path = NETWORK_MANAGER_LOG) -> str:
    """Read the last requested number of Network Manager log lines."""
    if lines < 1:
        raise ValueError("lines must be greater than zero")

    if not path.is_file():
        raise FileNotFoundError(f"Network Manager log not found: {path}")

    with path.open("r", encoding="utf-8", errors="replace") as log_file:
        recent_lines = deque(log_file, maxlen=lines)
        return "\n".join(line.rstrip("\r\n") for line in recent_lines)
