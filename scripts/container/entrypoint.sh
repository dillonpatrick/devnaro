#!/usr/bin/env sh
set -eu

# Keep the prompt identity in the persistent home volume, but normalize older
# versions of the DevBox prompt so repeated starts never stack prefixes.
ZSHRC="${HOME}/.zshrc"
PROMPT_MARKER="# DevBox prompt identity"

if [ -f "$ZSHRC" ]; then
    sed -i '/^# DevBox prompt identity$/,/^PROMPT=/d' "$ZSHRC"
    cat >> "$ZSHRC" <<'EOF'

# DevBox prompt identity
# Compact two-line prompt: container, current directory, Git branch, command.
setopt PROMPT_SUBST
PROMPT='%F{green}[DEVBOX]%f %F{cyan}%1~%f %F{yellow}$(git_prompt_info)%f
%F{green}❯%f '
EOF
fi

# A fresh marker is created whenever the container starts or restarts.
: > /tmp/devbox-welcome-pending
exec "$@"
