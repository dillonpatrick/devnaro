#!/usr/bin/env bash
set -euo pipefail

echo "==> Stopping DevBox..."

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "==> Removing DevBox container, Compose network, and DevBox home volume..."

docker compose --project-directory "$DEVBOX_DIR" -f "$DEVBOX_DIR/docker/docker-compose.yml" down --volumes --remove-orphans

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
echo
echo "The DevBox home volume contained shell configuration and Network Manager state."
echo "These settings will be recreated with defaults the next time DevBox starts."
echo
