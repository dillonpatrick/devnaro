#!/usr/bin/env bash
# Canonical metadata for the DevBox host CLI.
# Source this file from host scripts; keep command names and descriptions here.

DEVBOX_HOST_ALIASES=(enter)

DEVBOX_HOST_COMMANDS=(
    start shell stop clean restart recreate recreate-all status info logs networks doctor ci config manager help
)

declare -A DEVBOX_HOST_COMMAND_DESCRIPTIONS=(
    [start]="Build (if needed) and start DevBox"
    [shell]="Enter the running DevBox container (default)"
    [stop]="Stop the container without removing resources"
    [clean]="Remove DevBox containers, networks, volumes, and local images"
    [restart]="Restart the existing container"
    [recreate]="Recreate the container and network, preserving its home volume"
    [recreate-all]="Rebuild all DevBox resources, including the home volume"
    [status]="Show container status"
    [info]="Show container environment and host integrations"
    [logs]="Show container logs"
    [networks]="List networks connected to DevBox"
    [doctor]="Run health checks inside the container"
    [ci]="Run GitHub Actions locally with act"
    [config]="Show or change machine-specific configuration"
    [manager]="Manage the Network Manager"
    [help]="Show this help message"
)

DEVBOX_HOST_SUBCOMMANDS_config=(show get set)
DEVBOX_HOST_SUBCOMMANDS_manager=(status logs)
DEVBOX_HOST_CONFIG_KEYS=(workspace)

declare -A DEVBOX_HOST_SUBCOMMAND_DESCRIPTIONS=(
    ["manager status"]="Show Network Manager process status"
    ["manager logs"]="Show Network Manager logs"
)

devbox_host_completion() {
    local -a words candidates
    local current command_name
    words=("$@")
    current=""
    if (( ${#words[@]} > 0 )); then
        current="${words[${#words[@]}-1]}"
    fi

    if (( ${#words[@]} <= 1 )); then
        candidates=("${DEVBOX_HOST_COMMANDS[@]}" "${DEVBOX_HOST_ALIASES[@]}" -h --help)
    else
        command_name="${words[0]}"
        case "$command_name" in
            config)
                if (( ${#words[@]} == 2 )); then
                    candidates=("${DEVBOX_HOST_SUBCOMMANDS_config[@]}")
                elif (( ${#words[@]} == 3 )); then
                    case "${words[1]}" in
                        get|set) candidates=("${DEVBOX_HOST_CONFIG_KEYS[@]}") ;;
                    esac
                fi
                ;;
            manager)
                if (( ${#words[@]} == 2 )); then
                    candidates=("${DEVBOX_HOST_SUBCOMMANDS_manager[@]}")
                fi
                ;;
        esac
    fi

    local candidate
    for candidate in "${candidates[@]}"; do
        [[ "$candidate" == "$current"* ]] && printf '%s\n' "$candidate"
    done
}
