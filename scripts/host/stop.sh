#!/usr/bin/env bash
set -euo pipefail

echo "==> Stopping DevBox..."

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
USER_UID="$(id -u)"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
CODE_SOCKET_PATH="$RUNTIME_DIR/devbox-code-$USER_UID.sock"
CODE_BRIDGE_PID="$RUNTIME_DIR/devbox-code-$USER_UID.pid"

echo "==> Removing DevBox container, Compose network, and DevBox home volume..."

docker compose --project-directory "$DEVBOX_DIR" -f "$DEVBOX_DIR/docker/docker-compose.yml" down --volumes --remove-orphans

if [[ -f "$CODE_BRIDGE_PID" ]]; then
    kill "$(cat "$CODE_BRIDGE_PID")" 2>/dev/null || true
fi
rm -f "$CODE_BRIDGE_PID" "$CODE_SOCKET_PATH"

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
echo "  - devbox_home volume"
echo "  - Host VS Code bridge process and socket"
echo
echo "The DevBox home volume contained shell configuration and Network Manager state."
echo "These settings will be recreated with defaults the next time DevBox starts."
echo
