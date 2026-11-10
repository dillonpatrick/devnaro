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

# Enable devbox-manager Zsh completion automatically for the container user.
if [ -f "$ZSHRC" ] && ! grep -q '^# DevBox CLI completion$' "$ZSHRC"; then
    cat >> "$ZSHRC" <<'EOF'

# DevBox CLI completion
eval "$(_DEVBOX_MANAGER_COMPLETE=zsh_source devbox-manager)"
EOF
fi

# A fresh marker is created whenever the container starts or restarts.
: > /tmp/devbox-welcome-pending
exec "$@"
