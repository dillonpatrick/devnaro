#!/usr/bin/env bash
# Canonical metadata for the DevBox host CLI.
# Source this file from host scripts; keep command names and descriptions here.

DEVBOX_HOST_COMMANDS=(
    start shell stop clean restart recreate recreate-all status info logs networks doctor config manager help
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
    [info]="Show DevBox stack, base image, and installed tools"
    [logs]="Show container logs"
    [networks]="List networks connected to DevBox"
    [doctor]="Run health checks inside the container"
    [config]="Show or change machine-specific configuration"
    [manager]="Manage the Network Manager"
    [help]="Show this help message"
)

DEVBOX_HOST_SUBCOMMANDS_config=(show get set)
DEVBOX_HOST_SUBCOMMANDS_manager=(status logs)
DEVBOX_HOST_CONFIG_KEYS=(workspace)

devbox_host_print_command_list() {
    local command_name
    for command_name in "${DEVBOX_HOST_COMMANDS[@]}"; do
        printf '  %-18s %s\n' "$command_name" "${DEVBOX_HOST_COMMAND_DESCRIPTIONS[$command_name]}"
    done
    printf '  %-18s %s\n' "manager status" "Show Network Manager process status"
    printf '  %-18s %s\n' "manager logs" "Show Network Manager logs"
}

devbox_host_completion() {
    local -a words candidates
    local current command_name
    words=("$@")
    current="${words[${#words[@]}-1]:-}"

    if (( ${#words[@]} <= 1 )); then
        candidates=("${DEVBOX_HOST_COMMANDS[@]}" enter -h --help)
    else
        command_name="${words[0]}"
        case "$command_name" in
            config)
                if (( ${#words[@]} == 2 )); then
                    candidates=("${DEVBOX_HOST_SUBCOMMANDS_config[@]}" -h --help)
                elif (( ${#words[@]} == 3 )); then
                    case "${words[1]}" in
                        get|set) candidates=("${DEVBOX_HOST_CONFIG_KEYS[@]}") ;;
                    esac
                fi
                ;;
            manager)
                if (( ${#words[@]} == 2 )); then
                    candidates=("${DEVBOX_HOST_SUBCOMMANDS_manager[@]}" -h --help)
                fi
                ;;
        esac
    fi

    local candidate
    for candidate in "${candidates[@]}"; do
        [[ "$candidate" == "$current"* ]] && printf '%s\n' "$candidate"
    done
}
