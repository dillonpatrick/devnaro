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

# Resolve and validate the selected stack without adding Python/YAML to the host.
FROM python:3.12-alpine3.22 AS stack-resolver

ARG STACK_NAME=default
WORKDIR /resolver
RUN mkdir -p /resolver/devbox_manager \
    && pip install --no-cache-dir "PyYAML==6.0.3"
COPY src/devbox_manager/packages_manifest.py ./devbox_manager/packages_manifest.py
COPY src/devbox_manager/stack_resolver.py ./devbox_manager/stack_resolver.py
COPY stacks/ ./stacks/
RUN mkdir -p /out \
    && python -m devbox_manager.stack_resolver \
        --stack-file "/resolver/stacks/${STACK_NAME}/stack.yaml" \
        --output-dir /out

# The host-side stack selection supplies this value from the validated stack.
# Alpine and Debian use the same Core setup contract, with distro-specific packages.
ARG BASE_IMAGE=alpine:3.22
FROM ${BASE_IMAGE} AS runtime

ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000
ARG DOCKER_GID=966
ARG DEVBOX_BOOTSTRAP_UV_VERSION=0.13.7
ARG OH_MY_ZSH_COMMIT=cca3bdfbef8c52ef8939ce7911ff68852b949daa
ARG TARGETARCH
ARG BASE_IMAGE

RUN mkdir -p /opt/devbox-config \
    && touch /opt/devbox-config/packages.txt /opt/devbox-config/package-warnings.txt

COPY --from=stack-resolver /out/ /opt/devbox-config/stack/
COPY docker/packages.txt /tmp/devbox-user-packages.txt

# Install only runtime requirements for the DevBox Core.
# Compiler toolchains and development headers are intentionally not part of the final image.
RUN set -eux; \
    if [ -f /etc/alpine-release ]; then \
      apk add --no-cache \
        bash ca-certificates curl docker-cli docker-cli-compose git gnupg \
        nano procps python3 py3-pip py3-setuptools unzip wget zsh \
        zsh-autosuggestions zsh-syntax-highlighting; \
      python3 --version | grep -E '^Python 3\\.12\\.'; \
    elif [ -f /etc/debian_version ]; then \
      . /etc/os-release; \
      test "$ID" = debian; \
      apt-get update; \
      apt-get install -y --no-install-recommends \
        bash ca-certificates curl git gnupg nano procps python3 python3-pip \
        python3-venv unzip wget zsh zsh-autosuggestions zsh-syntax-highlighting; \
      install -m 0755 -d /etc/apt/keyrings; \
      curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc; \
      chmod a+r /etc/apt/keyrings/docker.asc; \
      printf 'Types: deb\\nURIs: https://download.docker.com/linux/debian\\nSuites: %s\\nComponents: stable\\nArchitectures: %s\\nSigned-By: /etc/apt/keyrings/docker.asc\\n' "$VERSION_CODENAME" "$(dpkg --print-architecture)" \
        > /etc/apt/sources.list.d/docker.sources; \
      apt-get update; \
      apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin; \
      rm -rf /var/lib/apt/lists/*; \
    else \
      echo "Unsupported DevBox base image: expected Alpine or Debian." >&2; \
      exit 1; \
    fi

# Install stack and user-managed packages with the selected distribution's package manager.
RUN set -eu; \
    if [ -f /etc/alpine-release ]; then \
      cat /opt/devbox-config/stack/alpine-packages.txt /tmp/devbox-user-packages.txt \
        | awk '/^[[:space:]]*($|#)/ { next } NF != 1 || $1 !~ /^[A-Za-z0-9+_.-]+$/ { print "Invalid package entry at line " NR ": " $0 > "/dev/stderr"; exit 1 } { if (!seen[$1]++) print $1 }' \
        > /tmp/devbox-extra-packages; \
      set --; \
      while IFS= read -r package; do \
        [ -z "$package" ] && continue; \
        if apk search -e "$package" >/dev/null 2>&1; then set -- "$@" "$package"; \
        else warning="WARNING: Alpine package '$package' was not found; skipping."; printf '%s\\n' "$warning" >&2; printf '%s\\n' "$warning" >> /opt/devbox-config/package-warnings.txt; fi; \
      done < /tmp/devbox-extra-packages; \
      if [ "$#" -gt 0 ]; then apk add --no-cache "$@"; fi; \
    else \
      cat /opt/devbox-config/stack/debian-packages.txt /tmp/devbox-user-packages.txt \
        | awk '/^[[:space:]]*($|#)/ { next } NF != 1 || $1 !~ /^[A-Za-z0-9+_.-]+$/ { print "Invalid package entry at line " NR ": " $0 > "/dev/stderr"; exit 1 } { if (!seen[$1]++) print $1 }' \
        > /tmp/devbox-extra-packages; \
      if [ -s /tmp/devbox-extra-packages ]; then \
        xargs -r apt-get install -y --no-install-recommends < /tmp/devbox-extra-packages; \
        rm -rf /var/lib/apt/lists/*; \
      fi; \
    fi; \
    rm -f /tmp/devbox-user-packages.txt /tmp/devbox-extra-packages

# Install Terraform only when the selected stack declares it.
RUN set -eux; \
    TERRAFORM_VERSION="$(cat /opt/devbox-config/stack/terraform-version)"; \
    if [ -n "$TERRAFORM_VERSION" ]; then \
      case "$TARGETARCH" in amd64) TERRAFORM_ARCH=amd64 ;; arm64) TERRAFORM_ARCH=arm64 ;; *) echo "Unsupported Terraform architecture: $TARGETARCH" >&2; exit 1 ;; esac; \
      if command -v apk >/dev/null 2>&1; then TOOL_ARCH="$TERRAFORM_ARCH"; else TOOL_ARCH="$TERRAFORM_ARCH"; fi; \
      wget -q "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TOOL_ARCH}.zip" -O /tmp/terraform.zip; \
      unzip /tmp/terraform.zip -d /usr/local/bin; rm /tmp/terraform.zip; \
      terraform version | grep -F "Terraform v${TERRAFORM_VERSION}"; \
    fi

# Keep the bootstrap uv private to DevBox; install the stack's uv separately.
RUN python3 -m venv /opt/devbox-bootstrap-uv \
    && /opt/devbox-bootstrap-uv/bin/pip install --no-cache-dir "uv==${DEVBOX_BOOTSTRAP_UV_VERSION}"

WORKDIR /opt/devbox-cli
COPY pyproject.toml uv.lock ./
COPY src/devbox_manager/ ./src/devbox_manager/
COPY tests/unit/ ./tests/unit/

RUN python3 -m venv /opt/devbox-venv \
    && UV_PROJECT_ENVIRONMENT=/opt/devbox-venv /opt/devbox-bootstrap-uv/bin/uv sync --locked --all-extras \
    && UV_VERSION="$(cat /opt/devbox-config/stack/uv-version)" \
    && if [ -n "$UV_VERSION" ]; then \
         python3 -m venv /opt/uv-venv \
         && /opt/uv-venv/bin/pip install --no-cache-dir "uv==${UV_VERSION}" \
         && /opt/uv-venv/bin/uv --version | grep -F "uv ${UV_VERSION}"; \
       fi

ENV PATH="/opt/devbox-venv/bin:/opt/uv-venv/bin:$PATH"

# Keep Alpine's BusyBox account tooling and Debian's shadow tooling behind one contract.
RUN set -eux; \
    if [ -f /etc/alpine-release ]; then \
      if ! getent group "$DOCKER_GID" >/dev/null; then addgroup -g "$DOCKER_GID" docker_host; fi; \
      DOCKER_GROUP="$(getent group "$DOCKER_GID" | cut -d: -f1)"; \
      if ! getent group "$USER_GID" >/dev/null; then addgroup -g "$USER_GID" "$USERNAME"; fi; \
      USER_GROUP="$(getent group "$USER_GID" | cut -d: -f1)"; \
      adduser -D -u "$USER_UID" -G "$USER_GROUP" -s /bin/zsh -h "/home/$USERNAME" "$USERNAME"; \
    else \
      if ! getent group "$DOCKER_GID" >/dev/null; then groupadd --gid "$DOCKER_GID" docker_host; fi; \
      DOCKER_GROUP="$(getent group "$DOCKER_GID" | cut -d: -f1)"; \
      if ! getent group "$USER_GID" >/dev/null; then groupadd --gid "$USER_GID" "$USERNAME"; fi; \
      USER_GROUP="$(getent group "$USER_GID" | cut -d: -f1)"; \
      useradd --uid "$USER_UID" --gid "$USER_GROUP" --create-home --home-dir "/home/$USERNAME" --shell /bin/zsh "$USERNAME"; \
    fi; \
    usermod -aG "$DOCKER_GROUP" "$USERNAME" 2>/dev/null || addgroup "$USERNAME" "$DOCKER_GROUP"; \
    mkdir -p "/home/$USERNAME"; \
    chown -R "$USER_UID":"$USER_GID" "/home/$USERNAME"

USER $USERNAME
WORKDIR /home/$USERNAME
ENV PATH="/home/${USERNAME}/.local/bin:/opt/devbox-venv/bin:/opt/uv-venv/bin:$PATH"

RUN git init /home/${USERNAME}/.oh-my-zsh \
    && git -C /home/${USERNAME}/.oh-my-zsh remote add origin https://github.com/ohmyzsh/ohmyzsh.git \
    && git -C /home/${USERNAME}/.oh-my-zsh fetch --depth 1 origin "${OH_MY_ZSH_COMMIT}" \
    && git -C /home/${USERNAME}/.oh-my-zsh checkout --detach FETCH_HEAD \
    && cp /home/${USERNAME}/.oh-my-zsh/templates/zshrc.zsh-template /home/${USERNAME}/.zshrc \
    && sed -i 's/^ZSH_THEME=.*/ZSH_THEME="robbyrussell"/' /home/${USERNAME}/.zshrc \
    && sed -i 's/^plugins=(git)$/plugins=(git docker terraform uv)/' /home/${USERNAME}/.zshrc \
    && if [ -f /etc/alpine-release ]; then \
         AUTOSUGGESTIONS=/usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh; \
         SYNTAX_HIGHLIGHTING=/usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh; \
       else \
         AUTOSUGGESTIONS=/usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh; \
         SYNTAX_HIGHLIGHTING=/usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh; \
       fi \
    && printf '\\n# Zsh autosuggestions\\nsource %s\\n' "$AUTOSUGGESTIONS" >> /home/${USERNAME}/.zshrc \
    && printf '\\n# Zsh syntax highlighting\\nsource %s\\n' "$SYNTAX_HIGHLIGHTING" >> /home/${USERNAME}/.zshrc \
    && test "$(git -C /home/${USERNAME}/.oh-my-zsh rev-parse HEAD)" = "${OH_MY_ZSH_COMMIT}" \
    && if [ -x /opt/uv-venv/bin/uv ]; then /opt/uv-venv/bin/uv --version; fi

COPY network_manager/ /opt/network-manager/
COPY scripts/container/entrypoint.sh /usr/local/bin/devbox-entrypoint
COPY scripts/container/code /usr/local/bin/code
COPY --from=bridge-builder /devbox-host-bridge /usr/local/bin/devbox-host-bridge
COPY --from=bridge-builder /devbox-status /usr/local/bin/devbox-status

USER root
RUN mkdir -p /run/devbox-host \
    && cp /opt/devbox-config/stack/environment.sh /etc/profile.d/devbox-stack.sh \
    && chmod 644 /etc/profile.d/devbox-stack.sh \
    && grep -m1 '^version = ' /opt/devbox-cli/pyproject.toml | cut -d '"' -f2 > /etc/devbox-version \
    && test -s /etc/devbox-version \
    && chmod +x /usr/local/bin/devbox-entrypoint /usr/local/bin/code \
    && cat >> /etc/zsh/zshrc <<'EOF'

# Restore DevBox-managed tools after login profiles adjust PATH.
export PATH="/home/${USERNAME}/.local/bin:/opt/devbox-venv/bin:/opt/uv-venv/bin:${PATH}"
[ -f /etc/profile.d/devbox-stack.sh ] && source /etc/profile.d/devbox-stack.sh

function dm() { devbox-manager "$@"; }

if [[ -f /tmp/devbox-welcome-pending ]]; then
    rm -f /tmp/devbox-welcome-pending
    devbox-manager welcome
fi
EOF

USER $USERNAME
ENTRYPOINT ["/usr/local/bin/devbox-entrypoint"]
CMD ["sleep", "infinity"]
