#!/usr/bin/env bash
# Shared terminal presentation helpers for short host lifecycle commands.

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
    DEVBOX_UI_RESET='\\033[0m'
    DEVBOX_UI_CYAN='\\033[0;96m'
    DEVBOX_UI_GREEN='\\033[0;32m'
    DEVBOX_UI_BOLD='\\033[1m'
else
    DEVBOX_UI_RESET=''
    DEVBOX_UI_CYAN=''
    DEVBOX_UI_GREEN=''
    DEVBOX_UI_BOLD=''
fi

devbox_info() { printf '%b➜%b %s\\n' "$DEVBOX_UI_CYAN" "$DEVBOX_UI_RESET" "$1"; }
devbox_success() { printf '%b✔%b %s\\n' "$DEVBOX_UI_GREEN" "$DEVBOX_UI_RESET" "$1"; }
devbox_heading() { printf '\\n%b%s%b\\n' "${DEVBOX_UI_CYAN}${DEVBOX_UI_BOLD}" "$1" "$DEVBOX_UI_RESET"; }
