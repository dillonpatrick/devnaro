#!/usr/bin/env bash
set -euo pipefail

echo "==> Initializing DevBox..."

# ==========================================
# 1. Directory and environment configuration
# ==========================================

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

USERNAME="devuser"

# Workspace located at the same directory level as DevBox
WORKSPACE_PATH="${WORKSPACE_PATH:-$SCRIPT_DIR/../workspace}"

USER_UID=$(id -u)
USER_GID=$(id -g)

# Docker socket validation
if [[ ! -S /var/run/docker.sock ]]; then
    echo "ERROR: Docker socket not found."
    exit 1
fi

# Docker socket group ID
DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)

if [[ -z "$DOCKER_GID" ]]; then
    echo "ERROR: Unable to detect Docker GID."
    exit 1
fi

# Timezone
TZ=$(cat /etc/timezone 2>/dev/null || echo "UTC")

# ==========================================
# 2. Workspace preparation
# ==========================================

if [[ ! -d "$WORKSPACE_PATH" ]]; then
    echo "==> Creating workspace..."
    mkdir -p "$WORKSPACE_PATH"
else
    echo "==> Reusing existing workspace."
fi

# Resolve workspace to an absolute path
WORKSPACE_PATH="$(realpath "$WORKSPACE_PATH")"

# ==========================================
# 3. Environment configuration
# ==========================================

cat > .env <<EOF
USERNAME=$USERNAME
USER_UID=$USER_UID
USER_GID=$USER_GID
DOCKER_GID=$DOCKER_GID
TZ=$TZ
WORKSPACE_PATH=$WORKSPACE_PATH
EOF

echo "==> Environment configuration:"
cat .env

# ==========================================
# 4. Docker Compose validation
# ==========================================

echo "==> Validating Docker Compose configuration..."

docker compose config --quiet

# ==========================================
# 5. Build DevBox
# ==========================================

echo "==> Building DevBox..."

docker compose build

# ==========================================
# 6. Start DevBox
# ==========================================

echo "==> Starting DevBox..."

docker compose up -d

# ==========================================
# 7. Network Manager
# ==========================================

echo "==> Checking Network Manager..."

if docker compose exec -T devbox \
    sh -c 'pgrep -f "[/]opt/network-manager/manager.py" >/dev/null 2>&1'; then

    echo "==> Network Manager is already running."

else

    echo "==> Starting Network Manager..."

    # Initialize log file
    docker compose exec -T devbox \
        sh -c ': > /tmp/network-manager.log'

    # Start Network Manager in detached mode
    docker compose exec -d -T devbox \
        sh -c 'exec python3 -u /opt/network-manager/manager.py >> /tmp/network-manager.log 2>&1'

    # Wait for the process to initialize
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
        echo "==> Network Manager started successfully."
    else
        echo "ERROR: Network Manager failed to start."

        docker compose exec -T devbox \
            sh -c 'cat /tmp/network-manager.log'

        exit 1
    fi

fi

# ==========================================
# 8. Finalization
# ==========================================

echo
echo "=================================="
echo " DevBox started successfully!"
echo "=================================="
echo
echo "Workspace: $WORKSPACE_PATH"
echo "Network Manager: Running"
echo
echo "Entering DevBox..."
echo

exec docker compose exec devbox zsh