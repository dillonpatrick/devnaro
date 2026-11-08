#!/usr/bin/env bash
set -euo pipefail

echo "==> Stopping DevBox..."

# Navigate to the DevBox project directory
cd "$(dirname "${BASH_SOURCE[0]}")"

# ==========================================
# 1. Stop and remove DevBox resources
# ==========================================

echo "==> Removing DevBox containers, networks and volumes..."

docker compose down --volumes --remove-orphans

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