#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
BIN_DIR="$(printenv DEVNARO_BIN_DIR || printf '%s' "$HOME/.local/bin")"
CLI_TARGET="$BIN_DIR/devnaro"
CLI_SOURCE="$SCRIPT_DIR/scripts/host/devnaro"
XDG_CONFIG_HOME_VALUE="$(printenv XDG_CONFIG_HOME || printf '%s' "$HOME/.config")"
CONFIG_DIR="$XDG_CONFIG_HOME_VALUE/devnaro"
CONFIG_FILE="$CONFIG_DIR/config"
USER_UID="$(id -u)"
RUNTIME_DIR="$(printenv XDG_RUNTIME_DIR || printf '%s' /tmp)"
CODE_SOCKET_DIR="$RUNTIME_DIR/devnaro-host-$USER_UID"
CODE_SOCKET_PATH="$CODE_SOCKET_DIR/code.sock"
CODE_BRIDGE_PID="$RUNTIME_DIR/devnaro-code-$USER_UID.pid"
CODE_BRIDGE_LOG="$RUNTIME_DIR/devnaro-code-$USER_UID.log"

CONFIG_WORKSPACE=""
if [[ -f "$CONFIG_FILE" ]]; then
    CONFIG_WORKSPACE="$(awk -F= '$1 == "workspace_path" { sub(/^[^=]*=/, ""); print; exit }' "$CONFIG_FILE")"
fi
WORKSPACE_PATH="$(printenv WORKSPACE_PATH || true)"
if [[ -z "$WORKSPACE_PATH" ]]; then
    WORKSPACE_PATH="$CONFIG_WORKSPACE"
fi
if [[ -z "$WORKSPACE_PATH" && -f "$SCRIPT_DIR/.env" ]]; then
    WORKSPACE_PATH="$(awk -F= '$1 == "WORKSPACE_PATH" { sub(/^[^=]*=/, ""); print; exit }' "$SCRIPT_DIR/.env")"
fi
if [[ -z "$WORKSPACE_PATH" ]]; then
    WORKSPACE_PATH="$SCRIPT_DIR/../workspace"
fi
WORKSPACE_PATH="$(realpath -m "$WORKSPACE_PATH")"
SCRIPT_DIR="$(realpath "$SCRIPT_DIR")"

printf '\nThis will completely remove DevNaro from this host.\n'
printf '  DevNaro repository: %s\n' "$SCRIPT_DIR"
printf '  Workspace to preserve: %s\n' "$WORKSPACE_PATH"
printf '\nThe DevNaro container, network, home volume, local image, host integration,\n'
printf 'machine configuration, and generated local files will be removed.\n'
printf 'Files in the workspace will be kept.\n\n'
read -r -p 'Continue? [y/N] ' confirmation
case "$confirmation" in
    y|Y|yes|YES|Yes) ;;
    *)
        printf 'Uninstall cancelled.\n'
        exit 0
        ;;
esac

bash "$SCRIPT_DIR/scripts/host/clean.sh"
rm -f "$CODE_BRIDGE_LOG"

if [[ -L "$CLI_TARGET" ]]; then
    TARGET_SOURCE="$(readlink -f "$CLI_TARGET" || true)"
    if [[ "$TARGET_SOURCE" == "$CLI_SOURCE" ]]; then
        rm -- "$CLI_TARGET"
        printf 'Removed DevNaro command: %s\n' "$CLI_TARGET"
    else
        printf 'Kept unrelated symlink: %s\n' "$CLI_TARGET"
    fi
elif [[ -e "$CLI_TARGET" ]]; then
    printf 'Kept existing non-symlink file: %s\n' "$CLI_TARGET"
fi

for SHELL_CONFIG in "$HOME/.bashrc" "$HOME/.zshrc"; do
    [[ -f "$SHELL_CONFIG" ]] || continue
    TEMP_CONFIG="$(mktemp)"
    awk '
        $0 == "# >>> DevNaro PATH >>>" { skip = 1; next }
        $0 == "# <<< DevNaro PATH <<<" { skip = 0; next }
        !skip { print }
    ' "$SHELL_CONFIG" > "$TEMP_CONFIG"

    if ! cmp -s "$SHELL_CONFIG" "$TEMP_CONFIG"; then
        cat "$TEMP_CONFIG" > "$SHELL_CONFIG"
        printf 'Removed DevNaro PATH entry from %s\n' "$SHELL_CONFIG"
    fi
    rm -f "$TEMP_CONFIG"
done

rm -rf -- "$CONFIG_DIR"
rm -f -- "$SCRIPT_DIR/.env"

printf '\nDevNaro was completely uninstalled.\n'
printf 'DevNaro repository preserved at: %s\n' "$SCRIPT_DIR"
printf 'Workspace preserved at: %s\n' "$WORKSPACE_PATH"
printf 'Open a new terminal to refresh PATH.\n'
