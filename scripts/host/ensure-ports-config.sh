#!/usr/bin/env bash
set -Eeuo pipefail

# Create the user-editable Compose port override on first use.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
EXAMPLE_FILE="$SCRIPT_DIR/docker/docker-compose.ports.example.yml"
LOCAL_FILE="$SCRIPT_DIR/docker/docker-compose.ports.yml"

if [[ ! -f "$LOCAL_FILE" ]]; then
    if [[ ! -f "$EXAMPLE_FILE" ]]; then
        printf 'DevBox port configuration template not found: %s\n' "$EXAMPLE_FILE" >&2
        exit 1
    fi

    cp "$EXAMPLE_FILE" "$LOCAL_FILE"
    printf 'Created local port configuration: %s\n' "$LOCAL_FILE"
fi
