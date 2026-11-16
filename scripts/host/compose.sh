#!/usr/bin/env bash
set -Eeuo pipefail

DEVNARO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

exec docker compose --project-directory "$DEVNARO_DIR" \
    -f "$DEVNARO_DIR/docker/docker-compose.yml" "$@"
