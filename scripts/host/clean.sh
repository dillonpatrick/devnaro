#!/usr/bin/env bash
set -euo pipefail

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$DEVBOX_DIR/scripts/host/ui.sh"

devbox_info "Cleaning DevBox resources..."

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
USER_UID="$(id -u)"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
CODE_SOCKET_PATH="$RUNTIME_DIR/devbox-code-$USER_UID.sock"
CODE_BRIDGE_PID="$RUNTIME_DIR/devbox-code-$USER_UID.pid"
CODE_BRIDGE_LOG="$RUNTIME_DIR/devbox-code-$USER_UID.log"
CODE_BRIDGE_BINARY="$RUNTIME_DIR/devbox-host-bridge-$USER_UID"
STATUS_BINARY="$RUNTIME_DIR/devbox-status-$USER_UID"
CODE_BRIDGE_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/devbox/vscode-workspaces"
bash "$DEVBOX_DIR/scripts/host/ensure-ports-config.sh"

# Remove only resources belonging to the DevBox Compose project.
bash "$DEVBOX_DIR/scripts/host/compose.sh" down --volumes --remove-orphans --rmi local

if [[ -f "$CODE_BRIDGE_PID" ]]; then
    kill "$(cat "$CODE_BRIDGE_PID")" 2>/dev/null || true
fi
rm -f "$CODE_BRIDGE_PID" "$CODE_SOCKET_PATH" "$CODE_BRIDGE_LOG" "$CODE_BRIDGE_BINARY" "$STATUS_BINARY"
rm -rf "$CODE_BRIDGE_CACHE_DIR"

echo
devbox_success "DevBox resources cleaned."
echo
devbox_heading "Preserved:"
echo "  - Workspace files"
echo "  - Containers and volumes from other Compose projects"
echo "  - Images not built by the DevBox Compose project"
echo
devbox_heading "Removed:"
echo "  - DevBox container and Compose network"
echo "  - DevBox Compose-managed volumes (including devbox_home)"
echo "  - DevBox-local images"
echo "  - Host VS Code bridge process and socket"
echo
