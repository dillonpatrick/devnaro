#!/usr/bin/env sh
set -eu

# Add a persistent visual identity to interactive Zsh sessions. The home
# directory is a named volume, so configure it at container startup rather
# than relying only on the image's initial .zshrc.
ZSHRC="${HOME}/.zshrc"
PROMPT_MARKER="# DevBox prompt identity"

if [ -f "$ZSHRC" ] && ! grep -Fq "$PROMPT_MARKER" "$ZSHRC"; then
    cat >> "$ZSHRC" <<'EOF'

# DevBox prompt identity
# Keep the active Zsh theme and Git decorations, but make the container obvious.
PROMPT="%F{green}[DEVBOX]%f ${PROMPT}"
EOF
fi

# A fresh marker is created whenever the container starts or restarts.
: > /tmp/devbox-welcome-pending
exec "$@"
