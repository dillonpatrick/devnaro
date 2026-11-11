#!/usr/bin/env bash
set -Eeuo pipefail

# Remove only the host command shortcut and PATH entries managed by DevBox.
# The repository, workspace, Docker resources, and user configuration are preserved.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
BIN_DIR="${DEVBOX_BIN_DIR:-$HOME/.local/bin}"
CLI_TARGET="$BIN_DIR/devbox"
CLI_SOURCE="$SCRIPT_DIR/scripts/host/devbox"

if [[ -L "$CLI_TARGET" ]]; then
    TARGET_SOURCE="$(readlink -f "$CLI_TARGET")"
    if [[ "$TARGET_SOURCE" == "$CLI_SOURCE" ]]; then
        rm -- "$CLI_TARGET"
        printf 'Removed DevBox command: %s\\n' "$CLI_TARGET"
    else
        printf 'Kept unrelated symlink: %s\\n' "$CLI_TARGET"
    fi
elif [[ -e "$CLI_TARGET" ]]; then
    printf 'Kept existing non-symlink file: %s\\n' "$CLI_TARGET"
else
    printf 'DevBox command shortcut not found: %s\\n' "$CLI_TARGET"
fi

# Remove only the PATH block created by install.sh.
for SHELL_CONFIG in "$HOME/.bashrc" "$HOME/.zshrc"; do
    [[ -f "$SHELL_CONFIG" ]] || continue

    TEMP_CONFIG="$(mktemp)"
    awk '
        $0 == "# >>> DevBox PATH >>>" { skip = 1; next }
        $0 == "# <<< DevBox PATH <<<" { skip = 0; next }
        !skip { print }
    ' "$SHELL_CONFIG" > "$TEMP_CONFIG"

    if ! cmp -s "$SHELL_CONFIG" "$TEMP_CONFIG"; then
        cat "$TEMP_CONFIG" > "$SHELL_CONFIG"
        printf 'Removed DevBox PATH entry from %s\\n' "$SHELL_CONFIG"
    fi
    rm -f "$TEMP_CONFIG"
done

printf '\\nDevBox host command uninstalled.\\n'
printf 'The DevBox repository, workspace, Docker containers, images, volumes, and configuration were left untouched.\\n'
printf 'Open a new terminal (or refresh your shell) to update PATH in the current session.\\n'
