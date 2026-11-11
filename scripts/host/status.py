#!/usr/bin/env python3
"""Render Docker Compose container status in a compact, readable format."""

from __future__ import annotations

import json
import os
import sys
import textwrap
from typing import Any


RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"


def color_enabled() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def paint(value: str, style: str, enabled: bool) -> str:
    return f"{style}{value}{RESET}" if enabled else value


def load_containers(raw: str) -> list[dict[str, Any]]:
    """Accept Compose JSON array/object and newline-delimited JSON."""
    raw = raw.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in raw.splitlines() if line.strip()]

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def status_style(status: str) -> str:
    normalized = status.lower()
    if normalized.startswith("up") or normalized == "running":
        return GREEN
    if "exited" in normalized or "dead" in normalized:
        return RED
    return YELLOW


def format_ports(publishers: Any) -> list[str]:
    if not isinstance(publishers, list):
        return []
    formatted = []
    for publisher in publishers:
        if not isinstance(publisher, dict):
            continue
        published = publisher.get("PublishedPort")
        target = publisher.get("TargetPort")
        protocol = publisher.get("Protocol", "tcp")
        host = publisher.get("URL") or "0.0.0.0"
        if published:
            formatted.append(f"{host}:{published}->{target}/{protocol}")
        elif target:
            formatted.append(f"{target}/{protocol}")
    return formatted


def render(containers: list[dict[str, Any]], color: bool | None = None) -> str:
    if color is None:
        color = color_enabled()

    if not containers:
        return (
            paint("DevBox container", BOLD, color)
            + "\n"
            + paint("  No container found. Start it with: devbox start", YELLOW, color)
        )

    lines: list[str] = []
    for index, container in enumerate(containers):
        name = str(container.get("Name") or container.get("Service") or "devbox")
        image = str(container.get("Image") or "Unknown")
        state = str(container.get("Status") or container.get("State") or "Unknown")
        created = str(container.get("CreatedAt") or container.get("RunningFor") or "Unknown")
        service = str(container.get("Service") or "devbox")

        lines.append(paint(f"DEVBOX  {name}", BOLD + CYAN, color))
        lines.append(f"  {'Service':<10} {service}")
        lines.append(f"  {'Image':<10} {image}")
        lines.append(f"  {'Status':<10} {paint(state, status_style(state), color)}")
        lines.append(f"  {'Created':<10} {created}")

        ports = format_ports(container.get("Publishers"))
        if ports:
            lines.append(f"  {'Ports':<10} {ports[0]}")
            for port in ports[1:]:
                lines.append(f"  {'':<10} {port}")
        else:
            lines.append(f"  {'Ports':<10} None")

        if index < len(containers) - 1:
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    try:
        raw = sys.stdin.read()
        containers = load_containers(raw)
    except (json.JSONDecodeError, OSError) as error:
        print(f"Unable to read Docker Compose status: {error}", file=sys.stderr)
        return 1

    print(render(containers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
