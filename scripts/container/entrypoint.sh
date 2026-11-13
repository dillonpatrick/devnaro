#!/usr/bin/env sh
set -eu

# Normalize DevBox-managed Zsh configuration in the persistent home volume.
ZSHRC="${HOME}/.zshrc"

if [ -f "$ZSHRC" ]; then
    # Remove the legacy prompt block, if present.
    sed -i '/^# DevBox prompt identity$/,/^PROMPT=/d' "$ZSHRC"

    # Older broken prompt writes could leave shell-script fragments after the
    # managed marker. Rebuild the managed tail instead of trying to patch it.
    sed -i '/^# BEGIN DEVBOX PROMPT THEME$/,$d' "$ZSHRC"
    sed -i '/^# BEGIN DEVBOX CLI COMPLETION$/,$d' "$ZSHRC"
    sed -i '/^# DevBox CLI completion$/d; /_DEVBOX_MANAGER_COMPLETE=zsh_source devbox-manager/d' "$ZSHRC"

    # Remove obsolete plugin paths from persistent homes created by older
    # Alpine-based images. The Debian paths are re-added below.
    sed -i '\|zsh-autosuggestions\.zsh|d; \|zsh-syntax-highlighting\.zsh|d' "$ZSHRC"

    cat >> "$ZSHRC" <<'EOF'

# BEGIN DEVBOX PROMPT THEME
unsetopt PROMPT_SUBST
devbox_update_prompt() {
    local branch=""
    if command git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        branch=$(command git symbolic-ref --quiet --short HEAD 2>/dev/null || command git rev-parse --short HEAD 2>/dev/null || true)
        [[ -n "$branch" ]] && branch="($branch)"
    fi

    PROMPT="%F{green}╭─ [DEVBOX] %f%F{cyan}%~%f ${branch}%f"$'\n'"%F{green}╰─❯%f "
}
precmd_functions+=(devbox_update_prompt)
devbox_update_prompt
# END DEVBOX PROMPT THEME

# Ensure DevBox-managed tools remain available after user Zsh configuration.
export PATH="${HOME}/.local/bin:/opt/devbox-venv/bin:/opt/uv-venv/bin:${PATH}"

# BEGIN DEVBOX ZSH PLUGINS
[[ -r /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh
[[ -r /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
# END DEVBOX ZSH PLUGINS
EOF
fi

# Make the mounted workspace easy to reach from the container home directory.
if [ -d "/workspace" ] && [ ! -e "${HOME}/workspace" ] && [ ! -L "${HOME}/workspace" ]; then
    ln -s /workspace "${HOME}/workspace"
fi

# Generate Zsh completion from the registered Typer command tree.
# The hidden __complete command returns candidates; no Click shell-source
# protocol or duplicated command list is needed.
if [ -f "$ZSHRC" ]; then
    cat >> "$ZSHRC" <<'EOF'

# BEGIN DEVBOX CLI COMPLETION
_devbox_completion() {
    local -a suggestions
    suggestions=("${(@f)$(devbox-manager __complete -- "${words[@]:2:$((CURRENT-1))}")}")
    compadd -- "${suggestions[@]}"
}
compdef _devbox_completion dm
# END DEVBOX CLI COMPLETION
EOF
fi

# A fresh marker is created whenever the container starts or restarts.
: > /tmp/devbox-welcome-pending
exec "$@"
