"""Helpers for inspecting the Network Manager process and logs."""

from collections import deque
from dataclasses import dataclass
import subprocess
from pathlib import Path

from devbox_manager.config import NETWORK_MANAGER_LOG, NETWORK_MANAGER_PROCESS


@dataclass(frozen=True)
class NetworkManagerProcess:
    """Useful runtime details for a Network Manager process."""

    pid: int
    ppid: int
    user: str
    state: str
    elapsed: str
    command: str


def process_status() -> tuple[bool, list[NetworkManagerProcess] | str]:
    """Return whether Network Manager is running and its process details."""
    process_pattern = f"[{NETWORK_MANAGER_PROCESS[0]}]{NETWORK_MANAGER_PROCESS[1:]}"

    try:
        result = subprocess.run(
            ["pgrep", "-f", process_pattern],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "pgrep is not installed (install the procps package)."

    if result.returncode != 0:
        return False, result.stderr.strip() or "No matching process found."

    processes: list[NetworkManagerProcess] = []
    for pid_text in result.stdout.split():
        try:
            details = subprocess.run(
                ["ps", "-p", pid_text, "-o", "pid=,ppid=,user=,stat=,etime=,args="],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return False, "ps is not installed (install the procps package)."

        if details.returncode != 0 or not details.stdout.strip():
            continue

        fields = details.stdout.strip().split(None, 5)
        if len(fields) < 6:
            continue

        try:
            processes.append(
                NetworkManagerProcess(
                    pid=int(fields[0]),
                    ppid=int(fields[1]),
                    user=fields[2],
                    state=fields[3],
                    elapsed=fields[4],
                    command=fields[5],
                )
            )
        except ValueError:
            continue

    if not processes:
        return False, "Process disappeared before its details could be read."

    return True, processes


def read_logs(lines: int = 50, path: Path = NETWORK_MANAGER_LOG) -> str:
    """Read the last requested number of Network Manager log lines."""
    if lines < 1:
        raise ValueError("lines must be greater than zero")

    if not path.is_file():
        raise FileNotFoundError(f"Network Manager log not found: {path}")

    with path.open("r", encoding="utf-8", errors="replace") as log_file:
        recent_lines = deque(log_file, maxlen=lines)
        return "\n".join(line.rstrip("\r\n") for line in recent_lines)
