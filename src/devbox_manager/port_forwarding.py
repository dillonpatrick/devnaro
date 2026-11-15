"""Persistent local TCP forwarding for services in project Compose networks."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILE = Path.home() / ".config/devbox/port-forwards.json"
LOG_FILE = Path("/tmp/port-forward-manager.log")
SYNC_INTERVAL = 3
_HOST_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class PortForward:
    local_port: int
    target_host: str
    target_port: int


def validate_port(port: int) -> int:
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("Ports must be integers between 1 and 65535.")
    return port


def validate_target_host(host: str) -> str:
    if not _HOST_PATTERN.fullmatch(host):
        raise ValueError("Target must be a container name, service name, or hostname.")
    return host


def load_forwards(path: Path = CONFIG_FILE) -> list[PortForward]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read port forwarding configuration: {error}") from error

    if not isinstance(raw, list):
        raise ValueError("Port forwarding configuration must be a JSON array.")

    forwards = []
    seen_ports = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each port forwarding entry must be an object.")
        local = validate_port(item.get("local_port"))
        target_port = validate_port(item.get("target_port"))
        host = validate_target_host(item.get("target_host", ""))
        if local in seen_ports:
            raise ValueError(f"Local port {local} is configured more than once.")
        seen_ports.add(local)
        forwards.append(PortForward(local, host, target_port))
    return forwards


def save_forwards(forwards: list[PortForward], path: Path = CONFIG_FILE) -> None:
    seen_ports = set()
    normalized = []
    for item in forwards:
        local = validate_port(item.local_port)
        target_port = validate_port(item.target_port)
        host = validate_target_host(item.target_host)
        if local in seen_ports:
            raise ValueError(f"Local port {local} is already configured.")
        seen_ports.add(local)
        normalized.append(
            {"local_port": local, "target_host": host, "target_port": target_port}
        )

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def add_forward(
    local_port: int, target_host: str, target_port: int, path: Path = CONFIG_FILE
) -> None:
    forwards = load_forwards(path)
    if any(item.local_port == local_port for item in forwards):
        raise ValueError(f"Local port {local_port} is already configured.")
    forwards.append(PortForward(local_port, target_host, target_port))
    save_forwards(forwards, path)


def remove_forward(local_port: int, path: Path = CONFIG_FILE) -> bool:
    forwards = load_forwards(path)
    remaining = [item for item in forwards if item.local_port != local_port]
    if len(remaining) == len(forwards):
        return False
    save_forwards(remaining, path)
    return True


class ForwardProcessManager:
    """Keep one socat listener alive for every configured local TCP forward."""

    def __init__(self) -> None:
        self.processes: dict[int, tuple[PortForward, subprocess.Popen]] = {}

    def synchronize(self) -> None:
        desired = {item.local_port: item for item in load_forwards()}
        for port, (current, process) in list(self.processes.items()):
            if desired.get(port) != current or process.poll() is not None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                self.processes.pop(port, None)
                print(f"[-] Stopped localhost:{port}", flush=True)

        for port, forward in desired.items():
            if port in self.processes:
                continue
            command = [
                "socat",
                f"TCP-LISTEN:{port},bind=127.0.0.1,reuseaddr,fork",
                f"TCP:{forward.target_host}:{forward.target_port},connect-timeout=3",
            ]
            log = LOG_FILE.open("a", encoding="utf-8")
            try:
                process = subprocess.Popen(
                    command, stdin=subprocess.DEVNULL, stdout=log, stderr=log
                )
            finally:
                log.close()
            self.processes[port] = (forward, process)
            print(
                f"[+] localhost:{port} -> {forward.target_host}:{forward.target_port}",
                flush=True,
            )

    def stop_all(self) -> None:
        for _, process in self.processes.values():
            process.terminate()
        for _, process in self.processes.values():
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        self.processes.clear()


def main() -> None:
    manager = ForwardProcessManager()
    print("[*] Port Forwarding Manager started", flush=True)
    while True:
        try:
            manager.synchronize()
        except (OSError, ValueError) as error:
            print(f"[!] Port forwarding sync failed: {error}", flush=True)
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
