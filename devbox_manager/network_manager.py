"""Helpers for inspecting the Network Manager process and logs."""

import subprocess
from collections import deque
from pathlib import Path

from devbox_manager.config import NETWORK_MANAGER_LOG, NETWORK_MANAGER_PROCESS


def process_status() -> tuple[bool, str]:
    """Return whether the Network Manager process is running."""
    result = subprocess.run(
        ["pgrep", "-af", f"[{NETWORK_MANAGER_PROCESS[0]}]{NETWORK_MANAGER_PROCESS[1:]}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0, result.stdout.strip()


def read_logs(lines: int = 50, path: Path = NETWORK_MANAGER_LOG) -> str:
    """Read the last requested number of Network Manager log lines."""
    if not path.is_file():
        raise FileNotFoundError(f"Network Manager log not found: {path}")

    with path.open("r", encoding="utf-8", errors="replace") as log_file:
        return "\n".join(deque(log_file, maxlen=lines)).rstrip()
