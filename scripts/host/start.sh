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
    BLUE='\033[0;96m'
    CYAN='\033[0;96m'
    WHITE='\033[1;96m'
else
    RESET=''
    BOLD=''
    DIM=''
    RED=''
    GREEN=''
    YELLOW=''
    BLUE='\033[0;96m'
    CYAN='\033[0;96m'
    WHITE='\033[1;96m'
fi

APP_NAME="DEVBOX"

TOTAL_STEPS=8

# Resolve the repository and package version before rendering the banner.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_VERSION="$(awk -F '"' '/^\[project\]/ { in_project=1; next } /^\[/ { in_project=0 } in_project && /^version = / { print $2; exit }' "$SCRIPT_DIR/pyproject.toml")"

if [[ -z "$APP_VERSION" ]]; then
    printf 'Unable to determine DevBox version from pyproject.toml.\n' >&2
    exit 1
fi

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


cd "$SCRIPT_DIR"
rm -f "$SCRIPT_DIR/docker/docker-compose.ports.yml"
compose() {
    bash "$SCRIPT_DIR/scripts/host/compose.sh" "$@"
}

resolve_bridge_image() {
    local image_name

    compose build devbox >&2

    image_name="$(compose config --images | head -n 1)"
    if [[ -z "$image_name" ]]; then
        error "Unable to resolve the DevBox image name from Docker Compose."
        return 1
    fi

    docker image inspect --format '{{.Id}}' "$image_name"
}

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
CODE_BRIDGE_BINARY="$RUNTIME_DIR/devbox-host-bridge-$USER_UID"
STATUS_BINARY="$RUNTIME_DIR/devbox-status-$USER_UID"
mkdir -p "$RUNTIME_DIR"

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

BRIDGE_CONTAINER_ID="$(compose ps --all --quiet devbox)"
IMAGE_PREBUILT=false
if [[ -n "$BRIDGE_CONTAINER_ID" ]]; then
    IMAGE_ID="$(docker inspect --format '{{.Image}}' "$BRIDGE_CONTAINER_ID")"
else
    info "Building the image to prepare the host VS Code bridge..."
    IMAGE_ID="$(resolve_bridge_image)"
    IMAGE_PREBUILT=true
fi

if [[ -z "$IMAGE_ID" ]]; then
    error "Unable to resolve the DevBox image for the host VS Code bridge."
    exit 1
fi

extract_host_binaries() {
    local image_id="$1"
    local container_id
    container_id="$(docker create "$image_id")"
    rm -f "$CODE_BRIDGE_BINARY" "$STATUS_BINARY"

    if ! docker cp "$container_id:/usr/local/bin/devbox-host-bridge" "$CODE_BRIDGE_BINARY" ||
       ! docker cp "$container_id:/usr/local/bin/devbox-status" "$STATUS_BINARY"; then
        docker rm "$container_id" >/dev/null
        rm -f "$CODE_BRIDGE_BINARY" "$STATUS_BINARY"
        return 1
    fi

    docker rm "$container_id" >/dev/null
    chmod 700 "$CODE_BRIDGE_BINARY" "$STATUS_BINARY"
}

if ! extract_host_binaries "$IMAGE_ID"; then
    info "The existing image is missing a DevBox host binary. Rebuilding..."
    IMAGE_ID="$(resolve_bridge_image)"
    if [[ -z "$IMAGE_ID" ]] || ! extract_host_binaries "$IMAGE_ID"; then
        error "Unable to extract DevBox host binaries from the image."
        exit 1
    fi
fi

if [[ ! -S "$CODE_SOCKET_PATH" ]] || [[ ! -f "$CODE_BRIDGE_PID" ]] || ! kill -0 "$(cat "$CODE_BRIDGE_PID")" 2>/dev/null; then
    rm -f "$CODE_SOCKET_PATH" "$CODE_BRIDGE_PID"
    info "Starting host VS Code bridge..."
    nohup "$CODE_BRIDGE_BINARY" \
        --socket "$CODE_SOCKET_PATH" \
        --workspace "$WORKSPACE_PATH" \
        --container "devbox" \
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
# 5. Determine the current container state
# ==========================================

CONTAINER_ID="$(compose ps --all --quiet devbox)"
CONTAINER_RUNNING=false

if [[ -n "$CONTAINER_ID" ]] && compose ps --status running --services | grep -Fxq devbox; then
    CONTAINER_RUNNING=true
fi

# ==========================================
# 6. Build only when the container is absent
# ==========================================

section 6 "Preparing DevBox"

if [[ -z "$CONTAINER_ID" ]]; then
    info "No existing container found. Building the DevBox image..."
    if [[ "$IMAGE_PREBUILT" != true ]]; then
        compose build
    fi
    success "DevBox image built successfully."
else
    info "Existing DevBox container found. Skipping image build."
fi

# ==========================================
# 7. Start without recreating existing containers
# ==========================================

section 7 "Starting DevBox container"

if [[ "$CONTAINER_RUNNING" == true ]]; then
    success "DevBox is already running. No restart or recreation needed."
elif [[ -n "$CONTAINER_ID" ]]; then
    info "Existing DevBox container is stopped. Starting it..."
    compose start devbox
    success "Existing DevBox container started."
else
    info "Creating and starting DevBox for the first time..."
    compose up -d
    success "DevBox container created and started."
fi

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
printf '  %bUser%b           %s\n' "${CYAN}" "${RESET}" "root"
printf '  %bNetwork Manager%b %s\n' "${CYAN}" "${RESET}" "Running"

printf '\n'
line

printf '\n'
printf '%b\n' "${WHITE}${BOLD}  Quick commands${RESET}"
printf '\n'
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox shell" "${RESET}" "Enter DevBox"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox status" "${RESET}" "Container status"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox info" "${RESET}" "DevBox container and host integrations"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox manager logs" "${RESET}" "Network Manager logs"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox networks" "${RESET}" "Docker networks"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox stop" "${RESET}" "Stop DevBox container"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox recreate-all" "${RESET}" "Recreate all DevBox resources"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox restart" "${RESET}" "Restart container only"
printf '  %b%-22s%b %s\n' "${GREEN}" "devbox recreate" "${RESET}" "Recreate container and network"

printf '\n'
line

printf '\n'
info "DevBox is ready. Use devbox shell to enter the container."

printf '\n'

trap - ERR
