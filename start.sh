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
APP_VERSION="1.0.0"

TOTAL_STEPS=7

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

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

USERNAME="devuser"

WORKSPACE_PATH="${WORKSPACE_PATH:-$SCRIPT_DIR/../workspace}"

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
EOF

success "Environment file generated."
detail ".env"

# ==========================================
# 4. Docker Compose validation
# ==========================================

section 4 "Validating Docker Compose"

info "Checking Docker Compose configuration..."

docker compose config --quiet

success "Docker Compose configuration is valid."

# ==========================================
# 5. Build DevBox
# ==========================================

section 5 "Building DevBox image"

info "Building Docker image..."

docker compose build

success "DevBox image built successfully."

# ==========================================
# 6. Start DevBox
# ==========================================

section 6 "Starting DevBox container"

info "Creating and starting container..."

docker compose up -d

success "DevBox container is running."

# ==========================================
# 7. Network Manager
# ==========================================

section 7 "Network Manager"

info "Checking Network Manager process..."

if docker compose exec -T devbox \
    sh -c 'pgrep -f "[/]opt/network-manager/manager.py" >/dev/null 2>&1'; then

    success "Network Manager is already running."

else

    info "Starting Network Manager..."

    docker compose exec -T devbox \
        sh -c ': > /tmp/network-manager.log'

    docker compose exec -d -T devbox \
        sh -c 'exec python3 -u /opt/network-manager/manager.py >> /tmp/network-manager.log 2>&1'

    MANAGER_STARTED=false

    for attempt in {1..5}; do

        if docker compose exec -T devbox \
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

        docker compose exec -T devbox \
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
printf '  %bShell alias%b    %s\n' "${CYAN}" "${RESET}" "devbox"

printf '\n'
line

printf '\n'
printf '%b\n' "${WHITE}${BOLD}  Quick commands${RESET}"
printf '\n'
printf '  %b%-18s%b %s\n' "${GREEN}" "devbox" "${RESET}" "Enter DevBox"
printf '  %b%-18s%b %s\n' "${GREEN}" "make status" "${RESET}" "Container status"
printf '  %b%-18s%b %s\n' "${GREEN}" "make manager-logs" "${RESET}" "Network Manager logs"
printf '  %b%-18s%b %s\n' "${GREEN}" "make networks" "${RESET}" "Docker networks"
printf '  %b%-18s%b %s\n' "${GREEN}" "make stop" "${RESET}" "Stop DevBox"

printf '\n'
line

printf '\n'
info "Entering DevBox shell..."
printf '\n'

trap - ERR

exec docker compose exec devbox zsh
