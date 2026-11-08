FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ==========================================
# 1. Build arguments
# ==========================================

ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000
ARG DOCKER_GID=966

# ==========================================
# 2. Essential tools
# ==========================================

RUN apt-get update && apt-get install -y \
    zsh \
    git \
    curl \
    nano \
    sudo \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    python3-docker \
    procps \
    unzip \
    gnupg \
    lsb-release \
    ca-certificates \
    wget \
    software-properties-common \
    zsh-autosuggestions \
    zsh-syntax-highlighting \
    && rm -rf /var/lib/apt/lists/*

# ==========================================
# 3. Terraform installation
# ==========================================

RUN wget -O- https://apt.releases.hashicorp.com/gpg | \
    gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com jammy main" \
    > /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update \
    && apt-get install -y terraform \
    && rm -rf /var/lib/apt/lists/*

# ==========================================
# 4. Docker CLI and Docker Compose
# ==========================================

RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu jammy stable" \
    > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y \
    docker-ce-cli \
    docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# ==========================================
# 5. Network Manager
# ==========================================

COPY --chown=root:root network_manager/ /opt/network-manager/

# ==========================================
# 6. DevBox Python CLI
# ==========================================

WORKDIR /opt/devbox-cli

COPY pyproject.toml ./
COPY src/devbox_manager/ ./src/devbox_manager/
COPY tests/unit/ ./tests/unit/

RUN python3 -m venv /opt/devbox-venv \
    && /opt/devbox-venv/bin/pip install --no-cache-dir ".[dev]"

ENV PATH="/opt/devbox-venv/bin:$PATH"

# ==========================================
# 7. User and group configuration
# ==========================================

RUN set -eux; \
    if ! getent group "$USER_GID" > /dev/null; then \
    groupadd --gid "$USER_GID" "$USERNAME"; \
    fi; \
    if getent passwd "$USERNAME" > /dev/null; then \
    usermod --uid "$USER_UID" --gid "$USER_GID" --shell /usr/bin/zsh "$USERNAME"; \
    else \
    if getent passwd "$USER_UID" > /dev/null; then \
    echo "ERROR: UID $USER_UID is already assigned to another user."; \
    exit 1; \
    fi; \
    useradd --uid "$USER_UID" --gid "$USER_GID" --create-home --shell /usr/bin/zsh "$USERNAME"; \
    fi; \
    echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/$USERNAME"; \
    chmod 0440 "/etc/sudoers.d/$USERNAME"; \
    if ! getent group "$DOCKER_GID" > /dev/null; then \
    groupadd --gid "$DOCKER_GID" docker_host; \
    fi; \
    DOCKER_GROUP="$(getent group "$DOCKER_GID" | cut -d: -f1)"; \
    usermod -aG "$DOCKER_GROUP,sudo" "$USERNAME"

# ==========================================
# 8. User environment configuration
# ==========================================

USER $USERNAME

WORKDIR /home/$USERNAME

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/home/${USERNAME}/.local/bin:$PATH"

# Install Oh My Zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" --unattended

# Configure Oh My Zsh plugins
RUN sed -i \
    's/^plugins=(git)$/plugins=(git docker terraform uv)/' \
    /home/$USERNAME/.zshrc

# Load system-installed Zsh plugins
RUN echo '\n# Zsh autosuggestions' >> /home/$USERNAME/.zshrc \
    && echo 'source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh' >> /home/$USERNAME/.zshrc \
    && echo '\n# Zsh syntax highlighting' >> /home/$USERNAME/.zshrc \
    && echo 'source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh' >> /home/$USERNAME/.zshrc

# ==========================================
# 9. Default shell
# ==========================================

# ==========================================
# 9. Welcome screen and container entrypoint
# ==========================================

COPY scripts/container/entrypoint.sh /usr/local/bin/devbox-entrypoint

USER root
RUN chmod +x /usr/local/bin/devbox-entrypoint \
    && cat >> /etc/zsh/zshrc <<'EOF'

# Short command for Network Manager operations, available in the container only.
function dm() { devbox-manager "$@"; }

# DevBox welcome screen: display once after each container start/restart.
if [[ -f /tmp/devbox-welcome-pending ]]; then
    rm -f /tmp/devbox-welcome-pending
    printf '\n'
    printf '\033[1;36m==============================================\033[0m\n'
    printf '\033[1;36m                 DEVBOX READY                 \033[0m\n'
    printf '\033[1;36m==============================================\033[0m\n'
    printf '\n'
    printf '  User:             %s\n' "$USER"
    printf '  Workspace:        %s\n' "$PWD"
    if pgrep -f '[/]opt/network-manager/manager.py' >/dev/null 2>&1; then
        printf '  Network Manager:  \033[1;32mRunning\033[0m\n'
    else
        printf '  Network Manager:  \033[1;33mNot detected\033[0m\n'
    fi
    printf '\n'
    printf '\033[1;37m  Useful commands\033[0m\n'
    printf '  cd /workspace                         Browse your projects\n'
    printf '  dm status                             Container status\n'
    printf '  dm doctor                             Environment health checks\n'
    printf '  dm networks                           Docker networks\n'
    printf '  dm network-manager logs               Network Manager logs\n'
    printf '  docker ps                             Running containers\n'
    printf '  docker compose up -d                  Start project services\n'
    printf '\n'
    printf '\033[2m  Tip: run commands from inside each project directory.\033[0m\n'
    printf '\n'
fi
EOF

USER $USERNAME

ENTRYPOINT ["/usr/local/bin/devbox-entrypoint"]
CMD ["sleep", "infinity"]
