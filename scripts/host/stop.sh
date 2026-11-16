#!/usr/bin/env bash
set -euo pipefail

DEVNARO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$DEVNARO_DIR/scripts/host/ui.sh"

devnaro_info "Stopping DevNaro container..."


bash "$DEVNARO_DIR/scripts/host/compose.sh" stop devnaro

echo
devnaro_success "DevNaro container stopped."
echo
devnaro_heading "Preserved:"
echo "  - DevNaro container (stopped)"
echo "  - DevNaro image and Compose network"
echo "  - devnaro_home volume"
echo "  - Workspace files"
echo "  - Other Docker resources"
echo
echo "Start it again with: devnaro start"
