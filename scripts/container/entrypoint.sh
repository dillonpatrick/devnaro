#!/usr/bin/env sh
set -eu

# The persistent home volume may have been created by the previous non-root
# image (UID/GID 1000). DevNaro now runs as root, so repair Oh My Zsh's
# completion directories before Zsh runs compaudit.
if [ -d "${HOME}/.oh-my-zsh" ]; then
    chown -R root:root "${HOME}/.oh-my-zsh"
    chmod -R go-w "${HOME}/.oh-my-zsh"
fi

# Normalize DevNaro-managed Zsh configuration in the persistent home volume.
ZSHRC="${HOME}/.zshrc"

if [ -f "$ZSHRC" ]; then
    # Remove the legacy prompt block, if present.
    sed -i '/^# DevNaro prompt identity$/,/^PROMPT=/d' "$ZSHRC"

    # Older broken prompt writes could leave shell-script fragments after the
    # managed marker. Rebuild the managed tail instead of trying to patch it.
    sed -i '/^# BEGIN DEVNARO PROMPT THEME$/,$d' "$ZSHRC"
    sed -i '/^# BEGIN DEVNARO CLI COMPLETION$/,$d' "$ZSHRC"
    sed -i '/^# DevNaro CLI completion$/d; /_DEVNARO_MANAGER_COMPLETE=zsh_source devnaro/d' "$ZSHRC"

    # Remove obsolete plugin paths from persistent homes created by older
    # Alpine-based images. The Debian paths are re-added below.
    sed -i '\|zsh-autosuggestions\.zsh|d; \|zsh-syntax-highlighting\.zsh|d' "$ZSHRC"

    cat >> "$ZSHRC" <<'EOF'

# BEGIN DEVNARO PROMPT THEME
unsetopt PROMPT_SUBST
devnaro_update_prompt() {
    local branch=""
    if command git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        branch=$(command git symbolic-ref --quiet --short HEAD 2>/dev/null || command git rev-parse --short HEAD 2>/dev/null || true)
        [[ -n "$branch" ]] && branch="($branch)"
    fi

    local venv_prefix=""
    [[ -n "${VIRTUAL_ENV:-}" ]] && venv_prefix="(%F{yellow}${VIRTUAL_ENV:t}%f) "
    PROMPT="%F{green}╭─ [DEVNARO] %f${venv_prefix}%F{cyan}%~%f ${branch}%f"$'\n'"%F{green}╰─❯%f "
}
precmd_functions+=(devnaro_update_prompt)
devnaro_update_prompt
# END DEVNARO PROMPT THEME

# Ensure DevNaro-managed tools remain available after user Zsh configuration.
export PATH="${HOME}/.local/bin:/opt/devnaro-venv/bin:/opt/uv-venv/bin:${PATH}"

# BEGIN DEVNARO ZSH PLUGINS
[[ -r /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh
[[ -r /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
# END DEVNARO ZSH PLUGINS
EOF
fi

# Keep Bash terminals (including VS Code's default terminal) consistent with Zsh.
BASHRC="${HOME}/.bashrc"
touch "$BASHRC"
sed -i '/^# BEGIN DEVNARO BASH CONFIG$/,/^# END DEVNARO BASH CONFIG$/d' "$BASHRC"
cat >> "$BASHRC" <<'EOF'

# BEGIN DEVNARO BASH CONFIG
export PATH="${HOME}/.local/bin:/opt/devnaro-venv/bin:/opt/uv-venv/bin:${PATH}"
dvn() { devnaro "$@"; }
devnaro_bash_prompt() {
    local branch=""
    if command git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        branch=$(command git symbolic-ref --quiet --short HEAD 2>/dev/null || command git rev-parse --short HEAD 2>/dev/null || true)
        [[ -n "$branch" ]] && branch=" ($branch)"
    fi
    local venv_prefix=""
    [[ -n "${VIRTUAL_ENV:-}" ]] && venv_prefix="(${VIRTUAL_ENV##*/}) "
    PS1="\\[\\e[32m\\]╭─ [DEVNARO] \\[\\e[33m\\]${venv_prefix}\\[\\e[36m\\]\\w\\[\\e[0m\\]\\[\\e[2m\\]${branch}\\[\\e[0m\\]\\n\\[\\e[32m\\]╰─❯\\[\\e[0m\\] "
}
PROMPT_COMMAND=devnaro_bash_prompt
# END DEVNARO BASH CONFIG
EOF

# Make the mounted workspace easy to reach from the container home directory.
if [ -d "/workspace" ] && [ ! -e "${HOME}/workspace" ] && [ ! -L "${HOME}/workspace" ]; then
    ln -s /workspace "${HOME}/workspace"
fi

# Generate Zsh completion from the registered Typer command tree.
# The hidden __complete command returns candidates; no Click shell-source
# protocol or duplicated command list is needed.
if [ -f "$ZSHRC" ]; then
    cat >> "$ZSHRC" <<'EOF'

# BEGIN DEVNARO CLI COMPLETION
_devnaro_completion() {
    local -a suggestions
    suggestions=("${(@f)$(devnaro __complete -- "${words[@]:2:$((CURRENT-1))}")}")
    compadd -- "${suggestions[@]}"
}
compdef _devnaro_completion dvn
# END DEVNARO CLI COMPLETION
EOF
fi

# A fresh marker is created whenever the container starts or restarts.
: > /tmp/devnaro-welcome-pending

# Keep configured localhost TCP forwards available for every container lifecycle.
if [ -f /opt/port-forwarding/manager.py ]; then
    python3 -u /opt/port-forwarding/manager.py >> /tmp/port-forward-manager.log 2>&1 &
fi

exec "$@"
