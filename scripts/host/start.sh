#!/usr/bin/env bash
set -Eeuo pipefail

# ==========================================
# DevBox - Terminal UI
# ==========================================

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
    RESET='\033[0m'
    BOLD='\033[1m'
    DIM='\033[2m'
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    WHITE='\033[1;37m'
else
    RESET=''
    BOLD=''
    DIM=''
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    WHITE=''
fi

APP_NAME="DEVBOX"

TOTAL_STEPS=8

# ==========================================
# UI functions
# ==========================================

line() {
    printf '%b\n' "${DIM}--------------------------------------------------${RESET}"
}

banner() {
    printf '\n'
    printf '%b\n' "${CYAN}${BOLD}"
    printf '  ____             ____             
'
    printf ' |  _ \  _____   _| __ )  _____  __
'
    printf ' | | | |/ _ \ \ / /  _ \ / _ \ \/ /
'
    printf ' | |_| |  __/\ V /| |_) | (_) >  <
'
    printf ' |____/ \___| \_/ |____/ \___/_/\_\
'
    printf '%b\n' "${RESET}"
    printf '%b\n' "${DIM}  Docker Development Environment${RESET}"
    printf '%b\n\n' "${DIM}  Version ${APP_VERSION}${RESET}"
}

section() {
    local number="$1"
    local description="$2"

    printf '\n'
    line
    printf '%b\n' "${BLUE}${BOLD}  [${number}/${TOTAL_STEPS}] ${description}${RESET}"
    line
}

info() {
    printf '  %b %s\n' "${CYAN}➜${RESET}" "$1"
}

success() {
    printf '  %b %s\n' "${GREEN}✔${RESET}" "$1"
}

warning() {
    printf '  %b %s\n' "${YELLOW}!${RESET}" "$1"
}

error() {
    printf '  %b %s\n' "${RED}✖${RESET}" "$1" >&2
}

detail() {
    printf '  %b%s%b\n' "${DIM}" "$1" "${RESET}"
}

# ==========================================
# Error handling
# ==========================================

handle_error() {
    local exit_code=$?
    local line_number=$1

    printf '\n'
    error "DevBox initialization failed."
    detail "Line: ${line_number}"
    detail "Exit code: ${exit_code}"
    printf '\n'

    exit "$exit_code"
}

trap 'handle_error $LINENO' ERR

# ==========================================
# Initialization
# ==========================================

clear 2>/dev/null || true
banner

printf '%b\n' "${WHITE}${BOLD}  Initializing development environment...${RESET}"
printf '\n'

# ==========================================
# 1. Directory and environment configuration
# ==========================================

section 1 "Environment configuration"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

# Keep the host banner version aligned with the package metadata.
APP_VERSION="$(awk -F '"' '/^\[project\]/ { in_project=1; next } /^\[/ { in_project=0 } in_project && /^version = / { print $2; exit }' "$SCRIPT_DIR/pyproject.toml")"

if [[ -z "$APP_VERSION" ]]; then
    error "Unable to determine DevBox version from pyproject.toml."
    exit 1
fi

cd "$SCRIPT_DIR"
compose() { docker compose --project-directory "$SCRIPT_DIR" -f "$SCRIPT_DIR/docker/docker-compose.yml" "$@"; }

USERNAME="devuser"

# Workspace precedence: explicit environment variable, machine config, default.
CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/devbox/config"
CONFIG_WORKSPACE=""

if [[ -f "$CONFIG_FILE" ]]; then
    CONFIG_WORKSPACE="$(awk -F= '$1 == "workspace_path" { sub(/^[^=]*=/, ""); print; exit }' "$CONFIG_FILE")"
fi

WORKSPACE_PATH="${WORKSPACE_PATH:-${CONFIG_WORKSPACE:-$SCRIPT_DIR/../workspace}}"

USER_UID=$(id -u)
USER_GID=$(id -g)

# Docker socket validation
if [[ ! -S /var/run/docker.sock ]]; then
    error "Docker socket not found."
    exit 1
fi

DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)

if [[ -z "$DOCKER_GID" ]]; then
    error "Unable to detect Docker GID."
    exit 1
fi

TZ=$(cat /etc/timezone 2>/dev/null || echo "UTC")

success "Docker socket detected."
success "Docker GID: ${DOCKER_GID}"
success "Host UID/GID: ${USER_UID}/${USER_GID}"
success "Timezone: ${TZ}"

# ==========================================
# 2. Workspace preparation
# ==========================================

section 2 "Workspace preparation"

if [[ ! -d "$WORKSPACE_PATH" ]]; then
    mkdir -p "$WORKSPACE_PATH"
    success "Workspace created."
else
    success "Existing workspace detected."
fi

WORKSPACE_PATH="$(realpath "$WORKSPACE_PATH")"

RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
CODE_SOCKET_PATH="$RUNTIME_DIR/devbox-code-$USER_UID.sock"
CODE_BRIDGE_PID="$RUNTIME_DIR/devbox-code-$USER_UID.pid"
CODE_BRIDGE_LOG="$RUNTIME_DIR/devbox-code-$USER_UID.log"

detail "Location: ${WORKSPACE_PATH}"

# ==========================================
# 3. Environment configuration
# ==========================================

section 3 "Generating environment configuration"

cat > .env <<EOF
USERNAME=$USERNAME
USER_UID=$USER_UID
USER_GID=$USER_GID
DOCKER_GID=$DOCKER_GID
TZ=$TZ
WORKSPACE_PATH=$WORKSPACE_PATH
CODE_SOCKET_PATH=$CODE_SOCKET_PATH
EOF

success "Environment file generated."
detail ".env"

# ==========================================
# 4. Host VS Code bridge
# ==========================================

section 4 "Host VS Code bridge"

if ! command -v python3 >/dev/null 2>&1; then
    error "Python 3 is required on the host for the VS Code bridge."
    exit 1
fi

if [[ ! -S "$CODE_SOCKET_PATH" ]] || [[ ! -f "$CODE_BRIDGE_PID" ]] || ! kill -0 "$(cat "$CODE_BRIDGE_PID")" 2>/dev/null; then
    rm -f "$CODE_SOCKET_PATH" "$CODE_BRIDGE_PID"
    info "Starting host VS Code bridge..."
    nohup python3 "$SCRIPT_DIR/scripts/host/code_bridge.py" \
        --socket "$CODE_SOCKET_PATH" \
        --workspace "$WORKSPACE_PATH" \
        >"$CODE_BRIDGE_LOG" 2>&1 &
    echo "$!" > "$CODE_BRIDGE_PID"

    BRIDGE_READY=false
    for attempt in {1..5}; do
        if [[ -S "$CODE_SOCKET_PATH" ]]; then
            BRIDGE_READY=true
            break
        fi
        sleep 1
    done

    if [[ "$BRIDGE_READY" != true ]]; then
        error "Host VS Code bridge failed to start. Check: $CODE_BRIDGE_LOG"
        exit 1
    fi
fi
success "Host VS Code bridge is ready."

# ==========================================
# 4. Docker Compose validation
# ==========================================

section 5 "Validating Docker Compose"

info "Checking Docker Compose configuration..."

compose config --quiet

success "Docker Compose configuration is valid."

# ==========================================
# 5. Build DevBox
# ==========================================

section 6 "Building DevBox image"

info "Building Docker image..."

compose build

success "DevBox image built successfully."

# ==========================================
# 6. Start DevBox
# ==========================================

section 7 "Starting DevBox container"

info "Creating and starting container..."

compose up -d

success "DevBox container is running."

# ==========================================
# 7. Network Manager
# ==========================================

section 8 "Network Manager"

info "Checking Network Manager process..."

if compose exec -T devbox \
    sh -c 'pgrep -f "[/]opt/network-manager/manager.py" >/dev/null 2>&1'; then

    success "Network Manager is already running."

else

    info "Starting Network Manager..."

    compose exec -T devbox \
        sh -c ': > /tmp/network-manager.log'

    compose exec -d -T devbox \
        sh -c 'exec python3 -u /opt/network-manager/manager.py >> /tmp/network-manager.log 2>&1'

    MANAGER_STARTED=false

    for attempt in {1..5}; do

        if compose exec -T devbox \
            sh -c 'pgrep -f "[/]opt/network-manager/manager.py" >/dev/null 2>&1'; then

            MANAGER_STARTED=true
            break

        fi

        sleep 1

    done

    if [[ "$MANAGER_STARTED" == true ]]; then
        success "Network Manager started successfully."
    else
        error "Network Manager failed to start."

        compose exec -T devbox \
            sh -c 'cat /tmp/network-manager.log'

        exit 1
    fi

fi

# ==========================================
# 8. Finalization
# ==========================================

printf '\n'
line

printf '%b\n' "${GREEN}${BOLD}  DEVBOX STARTED SUCCESSFULLY${RESET}"

line

printf '\n'
printf '  %bWorkspace%b       %s\n' "${CYAN}" "${RESET}" "$WORKSPACE_PATH"
printf '  %bContainer%b      %s\n' "${CYAN}" "${RESET}" "devbox"
printf '  %bUser%b           %s\n' "${CYAN}" "${RESET}" "$USERNAME"
printf '  %bNetwork Manager%b %s\n' "${CYAN}" "${RESET}" "Running"

printf '\n'
line

printf '\n'
printf '%b\n' "${WHITE}${BOLD}  Quick commands${RESET}"
printf '\n'
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox shell" "${RESET}" "Enter DevBox"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox status" "${RESET}" "Container status"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox manager logs" "${RESET}" "Network Manager logs"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox networks" "${RESET}" "Docker networks"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox stop" "${RESET}" "Remove DevBox resources"

printf '\n'
line

printf '\n'
info "DevBox is ready. Use devbox shell to enter the container."
printf '\n'

trap - ERR
