#!/usr/bin/env bash
set -euo pipefail

echo "==> Stopping DevBox container..."

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

docker compose --project-directory "$DEVBOX_DIR" -f "$DEVBOX_DIR/docker/docker-compose.yml" stop devbox

echo
echo "=================================="
echo " DevBox container stopped."
echo "=================================="
echo
echo "Preserved:"
echo "  - DevBox container (stopped)"
echo "  - DevBox image and Compose network"
echo "  - devbox_home volume"
echo "  - Workspace files"
echo "  - Other Docker resources"
echo
echo "Start it again with: devbox start"
