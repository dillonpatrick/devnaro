#!/usr/bin/env bash
set -euo pipefail

DEVNARO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
rm -f "$DEVNARO_DIR/docker/docker-compose.ports.yml"
source "$DEVNARO_DIR/scripts/host/ui.sh"

devnaro_info "Cleaning DevNaro resources..."

USER_UID="$(id -u)"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
CODE_SOCKET_DIR="$RUNTIME_DIR/devnaro-host-$USER_UID"
CODE_SOCKET_PATH="$CODE_SOCKET_DIR/code.sock"
CODE_BRIDGE_PID="$RUNTIME_DIR/devnaro-code-$USER_UID.pid"
CODE_BRIDGE_LOG="$RUNTIME_DIR/devnaro-code-$USER_UID.log"
CODE_BRIDGE_BINARY="$RUNTIME_DIR/devnaro-host-bridge-$USER_UID"
STATUS_BINARY="$RUNTIME_DIR/devnaro-status-$USER_UID"
CODE_BRIDGE_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/devnaro/vscode-workspaces"

# Remove only resources belonging to the DevNaro Compose project.
bash "$DEVNARO_DIR/scripts/host/compose.sh" down --volumes --remove-orphans --rmi local

if [[ -f "$CODE_BRIDGE_PID" ]]; then
    kill "$(cat "$CODE_BRIDGE_PID")" 2>/dev/null || true
fi
rm -f "$CODE_BRIDGE_PID" "$CODE_SOCKET_PATH" "$CODE_BRIDGE_LOG" "$CODE_BRIDGE_BINARY" "$STATUS_BINARY"
rmdir "$CODE_SOCKET_DIR" 2>/dev/null || true
rm -rf "$CODE_BRIDGE_CACHE_DIR"

echo
devnaro_success "DevNaro resources cleaned."
echo
devnaro_heading "Preserved:"
echo "  - Workspace files"
echo "  - Containers and volumes from other Compose projects"
echo "  - Images not built by the DevNaro Compose project"
echo
devnaro_heading "Removed:"
echo "  - DevNaro container and Compose network"
echo "  - DevNaro Compose-managed volumes (including devnaro_home)"
echo "  - DevNaro-local images"
echo "  - Host VS Code bridge process and socket"
echo
