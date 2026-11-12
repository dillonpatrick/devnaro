#!/usr/bin/env bash
set -Eeuo pipefail

DEVBOX_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

exec docker compose --project-directory "$DEVBOX_DIR" \
    -f "$DEVBOX_DIR/docker/docker-compose.yml" \
    -f "$DEVBOX_DIR/docker/docker-compose.ports.yml" "$@"
