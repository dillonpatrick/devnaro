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

info "Stopping DevBox container..."

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
bash "$DEVBOX_DIR/scripts/host/ensure-ports-config.sh"

bash "$DEVBOX_DIR/scripts/host/compose.sh" stop devbox

echo
success "DevBox container stopped."
echo
heading "Preserved:"
echo "  - DevBox container (stopped)"
echo "  - DevBox image and Compose network"
echo "  - devbox_home volume"
echo "  - Workspace files"
echo "  - Other Docker resources"
echo
echo "Start it again with: devbox start"
