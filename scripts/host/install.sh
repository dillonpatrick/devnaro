#!/usr/bin/env bash
set -Eeuo pipefail

# ==========================================
# DevNaro - Host installer
# ==========================================

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
BIN_DIR="${DEVNARO_BIN_DIR:-$HOME/.local/bin}"
CLI_SOURCE="$SCRIPT_DIR/scripts/host/devnaro"
CLI_TARGET="$BIN_DIR/devnaro"
source "$SCRIPT_DIR/scripts/host/command_registry.sh"

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
    RESET='\033[0m'
    BOLD='\033[1m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    CYAN='\033[0;96m'
    RED='\033[0;31m'
else
    RESET=''
    BOLD=''
    GREEN=''
    YELLOW=''
    CYAN='\033[0;96m'
    RED=''
fi

success() { printf '%b✔%b %s\n' "$GREEN" "$RESET" "$1"; }
info()    { printf '%b➜%b %s\n' "$CYAN" "$RESET" "$1"; }
warning() { printf '%b!%b %s\n' "$YELLOW" "$RESET" "$1"; }
error()   { printf '%b✖%b %s\n' "$RED" "$RESET" "$1" >&2; }

printf '\n%bDevNaro host installation%b\n\n' "$BOLD" "$RESET"

if ! command -v docker >/dev/null 2>&1; then
    error "Docker CLI was not found. Install Docker before configuring DevNaro."
    exit 1
fi

if [[ ! -f "$CLI_SOURCE" ]]; then
    error "Host CLI not found: $CLI_SOURCE"
    exit 1
fi

mkdir -p "$BIN_DIR"
BIN_DIR="$(cd -- "$BIN_DIR" && pwd)"

# Remove the legacy alias block created by earlier DevNaro installer versions.
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
        $0 == "# >>> DevNaro alias >>>" { skip = 1; next }
        $0 == "# <<< DevNaro alias <<<" { skip = 0; next }
        $0 == "# >>> DevNaro PATH >>>" { skip = 1; next }
        $0 == "# <<< DevNaro PATH <<<" { skip = 0; next }
        $0 == "# DevNaro shortcut" { next }
        $0 ~ /^alias devnaro=/ { next }
        !skip { print }
    ' "$SHELL_CONFIG" > "$TEMP_CONFIG"
    cat "$TEMP_CONFIG" > "$SHELL_CONFIG"
    rm -f "$TEMP_CONFIG"
fi

# Install/update the command symlink. The CLI resolves its real path,
# so it always locates the repository even when invoked from another directory.
if [[ -L "$CLI_TARGET" || -e "$CLI_TARGET" ]]; then
    if [[ ! -L "$CLI_TARGET" ]]; then
        error "$CLI_TARGET already exists and is not a symlink. Move it or choose another DEVNARO_BIN_DIR."
        exit 1
    fi
    rm "$CLI_TARGET"
fi

ln -s "$CLI_SOURCE" "$CLI_TARGET"
success "DevNaro command installed: $CLI_TARGET"

# Ensure the selected binary directory is added to PATH for future interactive shells.
PATH_LINE="export PATH=\"$BIN_DIR:\$PATH\""
if [[ -n "$SHELL_CONFIG" ]]; then
    touch "$SHELL_CONFIG"
    if ! grep -Fq "$PATH_LINE" "$SHELL_CONFIG"; then
        {
            printf '\n# >>> DevNaro PATH >>>\n'
            printf '%s\n' "$PATH_LINE"
            printf '# <<< DevNaro PATH <<<\n'
        } >> "$SHELL_CONFIG"
    fi
    success "PATH configuration updated in $SHELL_CONFIG"
    info "Open a new terminal, or run: source $SHELL_CONFIG"

    # Host completion queries the CLI's central command registry.
    if ! grep -Fq '# >>> DevNaro completion >>>' "$SHELL_CONFIG"; then
        if [[ "$HOST_SHELL" == "bash" ]]; then
            cat >> "$SHELL_CONFIG" <<'EOF'

# >>> DevNaro completion >>>
_devnaro_completion() {
    local -a suggestions
    suggestions=( $(devnaro __complete "${COMP_WORDS[@]:1}") )
    COMPREPLY=("${suggestions[@]}")
}
complete -F _devnaro_completion devnaro
# <<< DevNaro completion <<<
EOF
        elif [[ "$HOST_SHELL" == "zsh" ]]; then
            cat >> "$SHELL_CONFIG" <<'EOF'

# >>> DevNaro completion >>>
autoload -Uz compinit
if (( ! $+functions[compdef] )); then
    compinit
fi
_devnaro_completion() {
    local -a suggestions
    suggestions=("${(@f)$(devnaro __complete "${words[@]:2}")}")
    compadd -- "${suggestions[@]}"
}
compdef _devnaro_completion devnaro
# <<< DevNaro completion <<<
EOF
        fi
    fi
else
    warning "Add $BIN_DIR to PATH in your shell configuration."
fi

printf '\n%bHost commands%b\n' "${CYAN}${BOLD}" "$RESET"
for command_name in "${DEVNARO_HOST_COMMANDS[@]}"; do
    printf '  %-24s %s\n' "devnaro $command_name" "${DEVNARO_HOST_COMMAND_DESCRIPTIONS[$command_name]}"
done
for subcommand_name in "${DEVNARO_HOST_SUBCOMMANDS_manager[@]}"; do
    subcommand_key="manager $subcommand_name"
    printf '  %-24s %s\n' "devnaro $subcommand_key" "${DEVNARO_HOST_SUBCOMMAND_DESCRIPTIONS[$subcommand_key]}"
done
printf '\n%bRepository tasks%b (run from the DevNaro repository)\n' "${CYAN}${BOLD}" "$RESET"
printf '  %-24s %s\n' 'make install' 'Install the host-side devnaro command'
printf '  %-24s %s\n' 'make uninstall' 'Remove DevNaro from the host, preserving repository and workspace'
printf '\n'
