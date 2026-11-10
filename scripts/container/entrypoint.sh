#!/usr/bin/env sh
set -eu

# Keep a single-line prompt and preserve the active Oh My Zsh theme/Git info.
# Normalize any previous DevBox prompt snippets in the persistent home volume.
ZSHRC="${HOME}/.zshrc"

if [ -f "$ZSHRC" ]; then
    sed -i '/^# DevBox prompt identity$/,/^PROMPT=/d' "$ZSHRC"
    cat >> "$ZSHRC" <<'EOF'

# DevBox prompt identity
PROMPT="%F{green}[DEVBOX]%f ${PROMPT}"

# Ensure DevBox-managed tools remain available after user Zsh configuration.
export PATH="${HOME}/.local/bin:/opt/devbox-venv/bin:/opt/uv-venv/bin:${PATH}"
EOF
fi

# Replace the previous unsupported Click shell-source hook with native Zsh completion.
if [ -f "$ZSHRC" ]; then
    sed -i '/^# DevBox CLI completion$/d; /_DEVBOX_MANAGER_COMPLETE=zsh_source devbox-manager/d' "$ZSHRC"
    sed -i '/^# BEGIN DEVBOX CLI COMPLETION$/,/^# END DEVBOX CLI COMPLETION$/d' "$ZSHRC"
    if ! grep -q '^# BEGIN DEVBOX CLI COMPLETION$' "$ZSHRC"; then
        cat >> "$ZSHRC" <<'EOF'

# BEGIN DEVBOX CLI COMPLETION
autoload -Uz compinit
if (( ! $+functions[compdef] )); then
    compinit
fi

_devbox_manager_completion() {
    local -a commands
    commands=(status networks doctor network-manager)

    if (( CURRENT == 2 )); then
        compadd -- $commands
    elif [[ "${words[2]}" == "network-manager" && CURRENT == 3 ]]; then
        compadd -- status logs
    elif [[ "${words[2]}" == "network-manager" && "${words[3]}" == "logs" && CURRENT == 4 ]]; then
        compadd -- --lines -n
    fi
}

compdef _devbox_manager_completion devbox-manager
compdef _devbox_manager_completion dm
# END DEVBOX CLI COMPLETION
EOF
    fi
fi

# A fresh marker is created whenever the container starts or restarts.
: > /tmp/devbox-welcome-pending
exec "$@"
