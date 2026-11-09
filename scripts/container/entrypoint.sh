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
EOF
fi

# A fresh marker is created whenever the container starts or restarts.
: > /tmp/devbox-welcome-pending
exec "$@"
