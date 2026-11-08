FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

# ==========================================
# 1. Build arguments
# ==========================================

ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000
ARG DOCKER_GID=966
ARG TERRAFORM_VERSION=1.17.1
ARG UV_VERSION=0.13.7
ARG OH_MY_ZSH_COMMIT=cca3bdfbef8c52ef8939ce7911ff68852b949daa

# ==========================================
# 2. Essential tools
# ==========================================

RUN apt-get update && apt-get install -y \
    zsh \
    git \
    curl \
    nano \
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
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com noble main" \
    > /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update \
    && apt-get install -y terraform=${TERRAFORM_VERSION}-1 \
    && rm -rf /var/lib/apt/lists/*

# ==========================================
# 4. Docker CLI and Docker Compose
# ==========================================

RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" \
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

COPY pyproject.toml uv.lock ./
COPY src/devbox_manager/ ./src/devbox_manager/
COPY tests/unit/ ./tests/unit/

RUN python3 -m venv /opt/uv-venv \
    && /opt/uv-venv/bin/pip install --no-cache-dir "uv==${UV_VERSION}" \
    && python3 -m venv /opt/devbox-venv \
    && UV_PROJECT_ENVIRONMENT=/opt/devbox-venv /opt/uv-venv/bin/uv sync --locked --all-extras

ENV PATH="/opt/devbox-venv/bin:/opt/uv-venv/bin:$PATH"

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
    EXISTING_USER="$(getent passwd "$USER_UID" | cut -d: -f1 || true)"; \
    if [ -n "$EXISTING_USER" ]; then \
    usermod --login "$USERNAME" --home "/home/$USERNAME" --move-home --gid "$USER_GID" --shell /usr/bin/zsh "$EXISTING_USER"; \
    else \
    useradd --uid "$USER_UID" --gid "$USER_GID" --create-home --shell /usr/bin/zsh "$USERNAME"; \
    fi; \
    fi; \
    if ! getent group "$DOCKER_GID" > /dev/null; then \
    groupadd --gid "$DOCKER_GID" docker_host; \
    fi; \
    DOCKER_GROUP="$(getent group "$DOCKER_GID" | cut -d: -f1)"; \
    usermod -aG "$DOCKER_GROUP" "$USERNAME"

# ==========================================
# 8. User environment configuration
# ==========================================

USER $USERNAME

WORKDIR /home/$USERNAME

# uv is installed at an exact version in the isolated CLI virtual environment.
ENV PATH="/home/${USERNAME}/.local/bin:/opt/devbox-venv/bin:/opt/uv-venv/bin:$PATH"

# Install a reviewed, immutable Oh My Zsh commit instead of tracking master.
RUN git init /home/${USERNAME}/.oh-my-zsh \
    && git -C /home/${USERNAME}/.oh-my-zsh remote add origin https://github.com/ohmyzsh/ohmyzsh.git \
    && git -C /home/${USERNAME}/.oh-my-zsh fetch --depth 1 origin "${OH_MY_ZSH_COMMIT}" \
    && git -C /home/${USERNAME}/.oh-my-zsh checkout --detach FETCH_HEAD \
    && cp /home/${USERNAME}/.oh-my-zsh/templates/zshrc.zsh-template /home/${USERNAME}/.zshrc \
    && sed -i 's/^ZSH_THEME=.*/ZSH_THEME="robbyrussell"/' /home/${USERNAME}/.zshrc

# Fail the image build if a pinned tool does not match its requested version.
RUN terraform version | grep -F "Terraform v${TERRAFORM_VERSION}" \
    && uv --version | grep -F "uv ${UV_VERSION}" \
    && test "$(git -C /home/${USERNAME}/.oh-my-zsh rev-parse HEAD)" = "${OH_MY_ZSH_COMMIT}"

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
# 9. Host integration and welcome screen
# ==========================================
# ==========================================

COPY scripts/container/entrypoint.sh /usr/local/bin/devbox-entrypoint\nCOPY scripts/container/code /usr/local/bin/code

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
