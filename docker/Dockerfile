FROM --platform=$BUILDPLATFORM golang:1.24.3-alpine3.22 AS bridge-builder

ARG TARGETOS
ARG TARGETARCH
WORKDIR /src
COPY scripts/host/code_bridge.go ./code_bridge.go
COPY scripts/host/status.go ./status.go
COPY scripts/host/status_test.go ./status_test.go
RUN go test ./status.go ./status_test.go \
    && CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH go build -trimpath -ldflags="-s -w" -o /devbox-host-bridge ./code_bridge.go \
    && CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH go build -trimpath -ldflags="-s -w" -o /devbox-status ./status.go

FROM alpine:3.22

RUN mkdir -p /opt/devbox-config && touch /opt/devbox-config/packages.txt

ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000
ARG DOCKER_GID=966
ARG TERRAFORM_VERSION=1.17.1
ARG UV_VERSION=0.13.7
ARG OH_MY_ZSH_COMMIT=cca3bdfbef8c52ef8939ce7911ff68852b949daa
ARG TARGETARCH

# Start from the unmodified Alpine base and install the runtime/toolchain.
RUN apk add --no-cache \
    bash \
    build-base \
    ca-certificates \
    curl \
    docker-cli \
    docker-cli-compose \
    git \
    gnupg \
    libffi-dev \
    linux-headers \
    nano \
    openssl-dev \
    procps \
    python3 \
    python3-dev \
    py3-pip \
    py3-setuptools \
    unzip \
    wget \
    zsh \
    zsh-autosuggestions \
    zsh-syntax-highlighting \
    && python3 --version | grep -E '^Python 3\.12\.'

COPY docker/packages.txt /tmp/devbox-packages.txt

# Install valid user-selected packages; warn and skip names absent from Alpine repositories.
# Keep apk add itself strict so repository/network failures still fail the image build.
RUN set -eu; \
    apk update; \
    awk '/^[[:space:]]*($|#)/ { next } NF != 1 || $1 !~ /^[A-Za-z0-9+_.-]+$/ { print "Invalid package entry at line " NR ": " $0 > "/dev/stderr"; exit 1 } { print $1 }' /tmp/devbox-packages.txt > /tmp/devbox-extra-packages; \
    set --; \
    while IFS= read -r package; do \
        matches="$(apk search -e "$package" 2>/dev/null || true)"; \
        if [ -n "$matches" ]; then \
            set -- "$@" "$package"; \
        else \
            printf "WARNING: Alpine package '%s' was not found; skipping.\\n" "$package" >&2; \
        fi; \
    done < /tmp/devbox-extra-packages; \
    if [ "$#" -gt 0 ]; then \
        apk add --no-cache "$@"; \
    fi; \
    rm -f /tmp/devbox-packages.txt /tmp/devbox-extra-packages
# Install the pinned Terraform release for the target architecture.
RUN set -eux; \
    case "$TARGETARCH" in \
      amd64) TERRAFORM_ARCH=amd64 ;; \
      arm64) TERRAFORM_ARCH=arm64 ;; \
      *) echo "Unsupported Terraform architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    wget -q "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TERRAFORM_ARCH}.zip" -O /tmp/terraform.zip; \
    unzip /tmp/terraform.zip -d /usr/local/bin; \
    rm /tmp/terraform.zip; \
    terraform version | grep -F "Terraform v${TERRAFORM_VERSION}"

# Bootstrap uv in its own virtual environment, then sync the locked CLI env.
RUN python3 -m venv /opt/uv-venv \
    && /opt/uv-venv/bin/pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /opt/devbox-cli
COPY pyproject.toml uv.lock ./
COPY src/devbox_manager/ ./src/devbox_manager/
COPY tests/unit/ ./tests/unit/

RUN python3 -m venv /opt/devbox-venv \
    && UV_PROJECT_ENVIRONMENT=/opt/devbox-venv /opt/uv-venv/bin/uv sync --locked --all-extras

ENV PATH="/opt/devbox-venv/bin:/opt/uv-venv/bin:$PATH"

# Create an unprivileged user and grant access to the host Docker socket group.
RUN set -eux; \
    if ! getent group "$DOCKER_GID" >/dev/null; then addgroup -g "$DOCKER_GID" docker_host; fi; \
    DOCKER_GROUP="$(getent group "$DOCKER_GID" | cut -d: -f1)"; \
    if ! getent group "$USER_GID" >/dev/null; then addgroup -g "$USER_GID" "$USERNAME"; fi; \
    USER_GROUP="$(getent group "$USER_GID" | cut -d: -f1)"; \
    adduser -D -u "$USER_UID" -G "$USER_GROUP" -s /bin/zsh -h "/home/$USERNAME" "$USERNAME"; \
    addgroup "$USERNAME" "$DOCKER_GROUP"; \
    mkdir -p "/home/$USERNAME"; \
    chown -R "$USERNAME":"$USER_GROUP" "/home/$USERNAME"

USER $USERNAME
WORKDIR /home/$USERNAME
ENV PATH="/home/${USERNAME}/.local/bin:/opt/devbox-venv/bin:/opt/uv-venv/bin:$PATH"

# Install pinned Oh My Zsh and configure the DevBox plugins.
RUN git init /home/${USERNAME}/.oh-my-zsh \
    && git -C /home/${USERNAME}/.oh-my-zsh remote add origin https://github.com/ohmyzsh/ohmyzsh.git \
    && git -C /home/${USERNAME}/.oh-my-zsh fetch --depth 1 origin "${OH_MY_ZSH_COMMIT}" \
    && git -C /home/${USERNAME}/.oh-my-zsh checkout --detach FETCH_HEAD \
    && cp /home/${USERNAME}/.oh-my-zsh/templates/zshrc.zsh-template /home/${USERNAME}/.zshrc \
    && sed -i 's/^ZSH_THEME=.*/ZSH_THEME="robbyrussell"/' /home/${USERNAME}/.zshrc \
    && sed -i 's/^plugins=(git)$/plugins=(git docker terraform uv)/' /home/${USERNAME}/.zshrc \
    && printf '\n# Zsh autosuggestions\nsource /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh\n' >> /home/${USERNAME}/.zshrc \
    && printf '\n# Zsh syntax highlighting\nsource /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh\n' >> /home/${USERNAME}/.zshrc \
    && test "$(git -C /home/${USERNAME}/.oh-my-zsh rev-parse HEAD)" = "${OH_MY_ZSH_COMMIT}" \
    && uv --version | grep -F "uv ${UV_VERSION}"

COPY network_manager/ /opt/network-manager/
COPY scripts/container/entrypoint.sh /usr/local/bin/devbox-entrypoint
COPY scripts/container/code /usr/local/bin/code
COPY --from=bridge-builder /devbox-host-bridge /usr/local/bin/devbox-host-bridge
COPY --from=bridge-builder /devbox-status /usr/local/bin/devbox-status

USER root
RUN mkdir -p /run/devbox-host \
    && awk -F '"' '/^\[project\]/ { in_project=1; next } /^\[/ { in_project=0 } in_project && /^version = / { print $2; exit }' /opt/devbox-cli/pyproject.toml > /etc/devbox-version \
    && test -s /etc/devbox-version \
    && chmod +x /usr/local/bin/devbox-entrypoint /usr/local/bin/code \
    && cat >> /etc/zsh/zshrc <<'EOF'

# Restore DevBox-managed tools after login profiles adjust PATH.
export PATH="/home/${USERNAME}/.local/bin:/opt/devbox-venv/bin:/opt/uv-venv/bin:${PATH}"

function dm() { devbox-manager "$@"; }

if [[ -f /tmp/devbox-welcome-pending ]]; then
    rm -f /tmp/devbox-welcome-pending
    devbox-manager welcome
fi
EOF

USER $USERNAME
ENTRYPOINT ["/usr/local/bin/devbox-entrypoint"]
CMD ["sleep", "infinity"]
