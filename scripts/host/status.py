#!/usr/bin/env python3
"""Render Docker Compose container status in a compact, readable format."""

from __future__ import annotations

import json
import os
import sys
import re
import shutil
import textwrap
from datetime import datetime, timezone
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
    """Compact consecutive published/target ports into ranges."""
    if not isinstance(publishers, list):
        return []

    entries: list[tuple[str, int | None, int, str]] = []
    for publisher in publishers:
        if not isinstance(publisher, dict):
            continue
        target = publisher.get("TargetPort")
        if not isinstance(target, int):
            continue
        published = publisher.get("PublishedPort")
        if not isinstance(published, int):
            published = None
        host = str(publisher.get("URL") or "0.0.0.0")
        protocol = str(publisher.get("Protocol") or "tcp")
        entries.append((host, published, target, protocol))

    entries.sort(key=lambda item: (item[0], item[3], item[1] or -1, item[2]))
    groups: list[list[tuple[str, int | None, int, str]]] = []
    for entry in entries:
        if groups:
            previous = groups[-1][-1]
            same_mapping = entry[0] == previous[0] and entry[3] == previous[3]
            consecutive = (
                entry[1] is not None
                and previous[1] is not None
                and entry[1] == previous[1] + 1
                and entry[2] == previous[2] + 1
            )
            if same_mapping and consecutive:
                groups[-1].append(entry)
                continue
        groups.append([entry])

    formatted: list[str] = []
    for group in groups:
        host, published, target, protocol = group[0]
        last_published = group[-1][1]
        last_target = group[-1][2]
        if published is None:
            port_text = f"{target}/{protocol}"
        elif len(group) == 1:
            port_text = f"{host}:{published}->{target}/{protocol}"
        else:
            port_text = (
                f"{host}:{published}-{last_published}"
                f"->{target}-{last_target}/{protocol}"
            )
        formatted.append(port_text)
    return formatted


def format_created(container: dict[str, Any]) -> str:
    """Prefer Docker's relative age, falling back to a parsed creation time."""
    running_for = container.get("RunningFor")
    if running_for:
        return str(running_for)

    created_at = container.get("CreatedAt")
    if not created_at:
        return "Unknown"

    try:
        created = datetime.strptime(
            str(created_at), "%Y-%m-%d %H:%M:%S %z %Z"
        )
        elapsed = max(0, int((datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds()))
    except (ValueError, TypeError):
        return str(created_at)

    if elapsed < 60:
        return f"{elapsed} seconds ago"
    if elapsed < 3600:
        minutes = elapsed // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if elapsed < 86400:
        hours = elapsed // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = elapsed // 86400
    return f"{days} day{'s' if days != 1 else ''} ago"


def render(containers: list[dict[str, Any]], color: bool | None = None, width: int | None = None) -> str:
    if color is None:
        color = color_enabled()
    if width is None:
        width = shutil.get_terminal_size((100, 24)).columns
    width = max(48, min(width, 120))

    inner_width = width - 4
    title = "DevBox status"
    title_text = f" {title} "
    side = max(0, (inner_width - len(title_text)) // 2)
    top = "╭" + "─" * side + paint(title_text, BOLD + CYAN, color) + "─" * max(0, inner_width - side - len(title_text)) + "╮"
    bottom = "╰" + "─" * inner_width + "╯"
    lines = [top]

    if not containers:
        body = [paint("No container found. Start it with: devbox start", YELLOW, color)]
    else:
        body = []
        for index, container in enumerate(containers):
            name = str(container.get("Name") or container.get("Service") or "devbox")
            service = str(container.get("Service") or "devbox")
            image = str(container.get("Image") or "Unknown")
            state = str(container.get("Status") or container.get("State") or "Unknown")
            created = format_created(container)
            body.extend([
                paint(name.upper(), BOLD + CYAN, color),
                f"  {'Service':<10} {service}",
                f"  {'Image':<10} {image}",
                f"  {'Status':<10} {paint(state, status_style(state), color)}",
                f"  {'Created':<10} {created}",
            ])
            ports = format_ports(container.get("Publishers"))
            port_text = ",  ".join(ports) if ports else "None"
            wrapped_ports = textwrap.wrap(port_text, width=max(20, inner_width - 13), break_long_words=False, break_on_hyphens=False)
            body.append(f"  {'Ports':<10} {wrapped_ports[0] if wrapped_ports else 'None'}")
            for line in wrapped_ports[1:]:
                body.append(f"  {'':<10} {line}")
            if index < len(containers) - 1:
                body.append("")

    for line in body:
        plain_length = len(re.sub(r'\x1b\[[0-9;]*m', '', line))
        lines.append("│ " + line + " " * max(0, inner_width - plain_length) + " │")
    lines.append(bottom)
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
