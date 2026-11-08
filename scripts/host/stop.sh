#!/usr/bin/env bash
set -euo pipefail

echo "==> Stopping DevBox..."

# Navigate to the DevBox project directory
DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

# ==========================================
# 1. Stop and remove DevBox resources
# ==========================================

echo "==> Removing DevBox containers, networks and volumes..."

docker compose --project-directory "$DEVBOX_DIR" -f "$DEVBOX_DIR/docker/docker-compose.yml" down --volumes --remove-orphans

# ==========================================
# 2. Finalization
# ==========================================

echo
echo "=================================="
echo " DevBox successfully removed!"
echo "=================================="
echo
echo "Workspace preserved."
echo "Project containers preserved."
echo "Project volumes preserved."
echo "Docker images preserved."
echo