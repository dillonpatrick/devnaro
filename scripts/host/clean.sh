#!/usr/bin/env bash
set -euo pipefail

echo "==> Cleaning DevBox resources..."

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
USER_UID="$(id -u)"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
CODE_SOCKET_PATH="$RUNTIME_DIR/devbox-code-$USER_UID.sock"
CODE_BRIDGE_PID="$RUNTIME_DIR/devbox-code-$USER_UID.pid"

# Remove only resources belonging to the DevBox Compose project.
docker compose --project-directory "$DEVBOX_DIR" -f "$DEVBOX_DIR/docker/docker-compose.yml" down --volumes --remove-orphans --rmi local

if [[ -f "$CODE_BRIDGE_PID" ]]; then
    kill "$(cat "$CODE_BRIDGE_PID")" 2>/dev/null || true
fi
rm -f "$CODE_BRIDGE_PID" "$CODE_SOCKET_PATH"

echo
echo "=================================="
echo " DevBox resources cleaned."
echo "=================================="
echo
echo "Preserved:"
echo "  - Workspace files"
echo "  - Containers and volumes from other Compose projects"
echo "  - Images not built by the DevBox Compose project"
echo
echo "Removed:"
echo "  - DevBox container and Compose network"
echo "  - DevBox Compose-managed volumes (including devbox_home)"
echo "  - DevBox-local images"
echo "  - Host VS Code bridge process and socket"
echo
