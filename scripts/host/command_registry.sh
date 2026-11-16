#!/usr/bin/env bash
# Canonical metadata for the DevNaro host CLI.
# Source this file from host scripts; keep command names and descriptions here.

DEVNARO_HOST_ALIASES=(enter)

DEVNARO_HOST_COMMANDS=(
    start shell stop clean restart recreate recreate-all status info logs networks doctor ci config manager help
)

declare -A DEVNARO_HOST_COMMAND_DESCRIPTIONS=(
    [start]="Build (if needed) and start DevNaro"
    [shell]="Enter the running DevNaro container (default)"
    [stop]="Stop the container without removing resources"
    [clean]="Remove DevNaro containers, networks, volumes, and local images"
    [restart]="Restart the existing container"
    [recreate]="Recreate the container and network, preserving its home volume"
    [recreate-all]="Rebuild all DevNaro resources, including the home volume"
    [status]="Show container status"
    [info]="Show container environment and host integrations"
    [logs]="Show container logs"
    [networks]="List networks connected to DevNaro"
    [doctor]="Run health checks inside the container"
    [ci]="Run GitHub Actions locally with act"
    [config]="Show or change machine-specific configuration"
    [manager]="Manage the Network Manager"
    [help]="Show this help message"
)

DEVNARO_HOST_SUBCOMMANDS_config=(show get set)
DEVNARO_HOST_SUBCOMMANDS_manager=(status logs)
DEVNARO_HOST_CONFIG_KEYS=(workspace)

declare -A DEVNARO_HOST_SUBCOMMAND_DESCRIPTIONS=(
    ["manager status"]="Show Network Manager process status"
    ["manager logs"]="Show Network Manager logs"
)

devnaro_host_completion() {
    local -a words candidates
    local current command_name
    words=("$@")
    current=""
    if (( ${#words[@]} > 0 )); then
        current="${words[${#words[@]}-1]}"
    fi

    if (( ${#words[@]} <= 1 )); then
        candidates=("${DEVNARO_HOST_COMMANDS[@]}" "${DEVNARO_HOST_ALIASES[@]}" -h --help)
    else
        command_name="${words[0]}"
        case "$command_name" in
            config)
                if (( ${#words[@]} == 2 )); then
                    candidates=("${DEVNARO_HOST_SUBCOMMANDS_config[@]}")
                elif (( ${#words[@]} == 3 )); then
                    case "${words[1]}" in
                        get|set) candidates=("${DEVNARO_HOST_CONFIG_KEYS[@]}") ;;
                    esac
                fi
                ;;
            manager)
                if (( ${#words[@]} == 2 )); then
                    candidates=("${DEVNARO_HOST_SUBCOMMANDS_manager[@]}")
                fi
                ;;
        esac
    fi

    local candidate
    for candidate in "${candidates[@]}"; do
        [[ "$candidate" == "$current"* ]] && printf '%s\n' "$candidate"
    done
}
