#!/usr/bin/env bash
set -Eeuo pipefail

# ==========================================
# DevBox - Host installer
# ==========================================

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
BIN_DIR="${DEVBOX_BIN_DIR:-$HOME/.local/bin}"
CLI_SOURCE="$SCRIPT_DIR/scripts/host/devbox"
CLI_TARGET="$BIN_DIR/devbox"

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
    RESET='\033[0m'
    BOLD='\033[1m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    CYAN='\033[0;36m'
    RED='\033[0;31m'
else
    RESET=''
    BOLD=''
    GREEN=''
    YELLOW=''
    CYAN=''
    RED=''
fi

success() { printf '%b✔%b %s\n' "$GREEN" "$RESET" "$1"; }
info()    { printf '%b➜%b %s\n' "$CYAN" "$RESET" "$1"; }
warning() { printf '%b!%b %s\n' "$YELLOW" "$RESET" "$1"; }
error()   { printf '%b✖%b %s\n' "$RED" "$RESET" "$1" >&2; }

printf '\n%bDevBox host installation%b\n\n' "$BOLD" "$RESET"

if ! command -v docker >/dev/null 2>&1; then
    error "Docker CLI was not found. Install Docker before configuring DevBox."
    exit 1
fi

if [[ ! -f "$CLI_SOURCE" ]]; then
    error "Host CLI not found: $CLI_SOURCE"
    exit 1
fi

mkdir -p "$BIN_DIR"

# Remove the legacy alias block created by earlier DevBox installer versions.
HOST_SHELL="$(basename "${SHELL:-bash}")"
case "$HOST_SHELL" in
    bash) SHELL_CONFIG="$HOME/.bashrc" ;;
    zsh)  SHELL_CONFIG="$HOME/.zshrc" ;;
    *)
        SHELL_CONFIG=""
        warning "Could not identify a supported login shell. PATH may need manual configuration."
        ;;
esac

if [[ -n "$SHELL_CONFIG" && -f "$SHELL_CONFIG" ]]; then
    TEMP_CONFIG="$(mktemp)"
    awk '
        $0 == "# >>> DevBox alias >>>" { skip = 1; next }
        $0 == "# <<< DevBox alias <<<" { skip = 0; next }
        $0 == "# >>> DevBox PATH >>>" { skip = 1; next }
        $0 == "# <<< DevBox PATH <<<" { skip = 0; next }
        $0 == "# DevBox shortcut" { next }
        $0 ~ /^alias devbox=/ { next }
        !skip { print }
    ' "$SHELL_CONFIG" > "$TEMP_CONFIG"
    cat "$TEMP_CONFIG" > "$SHELL_CONFIG"
    rm -f "$TEMP_CONFIG"
fi

# Install/update the command symlink. The CLI resolves its real path,
# so it always locates the repository even when invoked from another directory.
if [[ -L "$CLI_TARGET" || -e "$CLI_TARGET" ]]; then
    if [[ ! -L "$CLI_TARGET" ]]; then
        error "$CLI_TARGET already exists and is not a symlink. Move it or choose another DEVBOX_BIN_DIR."
        exit 1
    fi
    rm "$CLI_TARGET"
fi

ln -s "$CLI_SOURCE" "$CLI_TARGET"
success "DevBox command installed: $CLI_TARGET"

# Ensure ~/.local/bin is added to PATH for future interactive shells.
PATH_LINE="export PATH=\"$BIN_DIR:\$PATH\""
if [[ -n "$SHELL_CONFIG" ]]; then
    touch "$SHELL_CONFIG"
    if ! grep -Fq "$PATH_LINE" "$SHELL_CONFIG"; then
        {
            printf '\n# >>> DevBox PATH >>>\n'
            printf '%s\n' "$PATH_LINE"
            printf '# <<< DevBox PATH <<<\n'
        } >> "$SHELL_CONFIG"
    fi
    success "PATH configuration updated in $SHELL_CONFIG"
    info "Open a new terminal, or run: source $SHELL_CONFIG"
else
    warning "Add $BIN_DIR to PATH in your shell configuration."
fi

printf '\n%bAvailable commands%b\n' "$BOLD" "$RESET"
printf '  devbox start\n'
printf '  devbox shell\n'
printf '  devbox status\n'
printf '  devbox networks\n'
printf '  devbox doctor\n'
printf '  devbox manager status\n'
printf '  devbox manager logs\n'
printf '  devbox restart\n'
printf '  devbox stop\n'
printf '  devbox config\n'
printf '\n'
