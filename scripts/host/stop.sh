#!/usr/bin/env bash
set -euo pipefail

echo "==> Stopping DevBox..."

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"\nUSER_UID="$(id -u)"\nRUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"\nCODE_SOCKET_PATH="$RUNTIME_DIR/devbox-code-$USER_UID.sock"\nCODE_BRIDGE_PID="$RUNTIME_DIR/devbox-code-$USER_UID.pid"

echo "==> Removing DevBox container, Compose network, and DevBox home volume..."

docker compose --project-directory "$DEVBOX_DIR" -f "$DEVBOX_DIR/docker/docker-compose.yml" down --volumes --remove-orphans\n\nif [[ -f "$CODE_BRIDGE_PID" ]]; then\n    kill "$(cat "$CODE_BRIDGE_PID")" 2>/dev/null || true\nfi\nrm -f "$CODE_BRIDGE_PID" "$CODE_SOCKET_PATH"

echo
echo "=================================="
echo " DevBox resources removed."
echo "=================================="
echo
echo "Preserved:"
echo "  - Workspace files"
echo "  - Containers from other Compose projects"
echo "  - Volumes from other Compose projects"
echo "  - Docker images"
echo
echo "Removed:"
echo "  - DevBox container and its Compose network"
echo "  - devbox_home volume\n  - Host VS Code bridge process and socket"
echo
echo "The DevBox home volume contained shell configuration and Network Manager state."
echo "These settings will be recreated with defaults the next time DevBox starts."
echo
