#!/usr/bin/env bash
set -euo pipefail

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$DEVBOX_DIR/scripts/host/ui.sh"

devbox_info "Stopping DevBox container..."

bash "$DEVBOX_DIR/scripts/host/ensure-ports-config.sh"

bash "$DEVBOX_DIR/scripts/host/compose.sh" stop devbox

echo
devbox_success "DevBox container stopped."
echo
devbox_heading "Preserved:"
echo "  - DevBox container (stopped)"
echo "  - DevBox image and Compose network"
echo "  - devbox_home volume"
echo "  - Workspace files"
echo "  - Other Docker resources"
echo
echo "Start it again with: devbox start"
