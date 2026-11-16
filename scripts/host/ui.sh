#!/usr/bin/env bash
# Shared terminal presentation helpers for short host lifecycle commands.

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
    DEVNARO_UI_RESET='\033[0m'
    DEVNARO_UI_CYAN='\033[0;96m'
    DEVNARO_UI_GREEN='\033[0;32m'
    DEVNARO_UI_BOLD='\033[1m'
else
    DEVNARO_UI_RESET=''
    DEVNARO_UI_CYAN=''
    DEVNARO_UI_GREEN=''
    DEVNARO_UI_BOLD=''
fi

devnaro_info() { printf '%b➜%b %s\n' "$DEVNARO_UI_CYAN" "$DEVNARO_UI_RESET" "$1"; }
devnaro_success() { printf '%b✔%b %s\n' "$DEVNARO_UI_GREEN" "$DEVNARO_UI_RESET" "$1"; }
devnaro_heading() { printf '\n%b%s%b\n' "${DEVNARO_UI_CYAN}${DEVNARO_UI_BOLD}" "$1" "$DEVNARO_UI_RESET"; }
