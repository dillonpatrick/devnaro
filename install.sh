#!/usr/bin/env bash
set -Eeuo pipefail

# ==========================================
# DevBox - Host installer
# ==========================================

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

success() {
    printf '%b✔%b %s\n' "$GREEN" "$RESET" "$1"
}

info() {
    printf '%b➜%b %s\n' "$CYAN" "$RESET" "$1"
}

warning() {
    printf '%b!%b %s\n' "$YELLOW" "$RESET" "$1"
}

error() {
    printf '%b✖%b %s\n' "$RED" "$RESET" "$1" >&2
}

printf '\n%bDevBox host setup%b\n\n' "$BOLD" "$RESET"

# The alias uses the Docker CLI on the host, so do not install
# or modify Docker as part of this script.
if ! command -v docker >/dev/null 2>&1; then
    error "Docker CLI was not found. Install Docker before configuring DevBox."
    exit 1
fi

HOST_SHELL="$(basename "${SHELL:-bash}")"

case "$HOST_SHELL" in
    bash)
        SHELL_CONFIG="$HOME/.bashrc"
        ;;
    zsh)
        SHELL_CONFIG="$HOME/.zshrc"
        ;;
    *)
        warning "Unsupported login shell: $HOST_SHELL"
        warning "Add the DevBox alias manually to your shell configuration:"
        printf "alias devbox='docker exec -it devbox zsh'\n"
        exit 0
        ;;
esac

ALIAS_LINE="alias devbox='docker exec -it devbox zsh'"
BEGIN_MARKER="# >>> DevBox alias >>>"
END_MARKER="# <<< DevBox alias <<<"

touch "$SHELL_CONFIG"

if grep -Fq "$BEGIN_MARKER" "$SHELL_CONFIG"; then
    # Replace the block managed by this installer, keeping the operation idempotent.
    TEMP_CONFIG="$(mktemp)"
    awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
        $0 == begin { skip = 1; next }
        $0 == end { skip = 0; next }
        !skip { print }
    ' "$SHELL_CONFIG" > "$TEMP_CONFIG"
    cat "$TEMP_CONFIG" > "$SHELL_CONFIG"
    rm -f "$TEMP_CONFIG"
elif grep -Fxq "$ALIAS_LINE" "$SHELL_CONFIG"; then
    success "DevBox alias already exists in $SHELL_CONFIG."
    info "Run 'source $SHELL_CONFIG' or open a new terminal to load it."
    exit 0
fi

{
    printf '\n%s\n' "$BEGIN_MARKER"
    printf '%s\n' "$ALIAS_LINE"
    printf '%s\n' "$END_MARKER"
} >> "$SHELL_CONFIG"

success "DevBox alias configured."
info "Shell configuration: $SHELL_CONFIG"
info "Run 'source $SHELL_CONFIG' or open a new terminal."
printf '\n'
printf '%bUsage%b\n' "$BOLD" "$RESET"
printf '  make start   # Start the DevBox container\n'
printf '  devbox       # Enter the container\n'
printf '  make stop    # Stop and remove DevBox resources\n'
printf '\n'
