#!/usr/bin/env bash
set -euo pipefail

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
    RESET='\033[0m'
    CYAN='\033[0;96m'
    GREEN='\033[0;32m'
    BOLD='\033[1m'
else
    RESET=''
    CYAN=''
    GREEN=''
    BOLD=''
fi

info() { printf '%b➜%b %s\n' "$CYAN" "$RESET" "$1"; }
success() { printf '%b✔%b %s\n' "$GREEN" "$RESET" "$1"; }
heading() { printf '\n%b%s%b\n' "${CYAN}${BOLD}" "$1" "$RESET"; }

info "Cleaning DevBox resources..."

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
USER_UID="$(id -u)"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
CODE_SOCKET_PATH="$RUNTIME_DIR/devbox-code-$USER_UID.sock"
CODE_BRIDGE_PID="$RUNTIME_DIR/devbox-code-$USER_UID.pid"
bash "$DEVBOX_DIR/scripts/host/ensure-ports-config.sh"

# Remove only resources belonging to the DevBox Compose project.
docker compose --project-directory "$DEVBOX_DIR" \
    -f "$DEVBOX_DIR/docker/docker-compose.yml" \
    -f "$DEVBOX_DIR/docker/docker-compose.ports.yml" down --volumes --remove-orphans --rmi local

if [[ -f "$CODE_BRIDGE_PID" ]]; then
    kill "$(cat "$CODE_BRIDGE_PID")" 2>/dev/null || true
fi
rm -f "$CODE_BRIDGE_PID" "$CODE_SOCKET_PATH"

echo
success "DevBox resources cleaned."
echo
heading "Preserved:"
echo "  - Workspace files"
echo "  - Containers and volumes from other Compose projects"
echo "  - Images not built by the DevBox Compose project"
echo
heading "Removed:"
echo "  - DevBox container and Compose network"
echo "  - DevBox Compose-managed volumes (including devbox_home)"
echo "  - DevBox-local images"
echo "  - Host VS Code bridge process and socket"
echo
