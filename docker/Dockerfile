ARG BASE_IMAGE=debian:trixie-slim

FROM --platform=$BUILDPLATFORM golang:1.24.3-bookworm AS bridge-builder

ARG TARGETOS
WORKDIR /src
COPY scripts/host/code_bridge.go ./code_bridge.go
COPY scripts/host/status.go ./status.go
COPY scripts/host/status_test.go ./status_test.go
COPY scripts/host/code_bridge_test.go ./code_bridge_test.go
RUN go test ./status.go ./status_test.go \
    && go test ./code_bridge.go ./code_bridge_test.go \
    && CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH go build -trimpath -ldflags="-s -w" -o /devnaro-host-bridge ./code_bridge.go \
    && CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH go build -trimpath -ldflags="-s -w" -o /devnaro-status ./status.go

# Resolve and validate the selected stack without adding Python/YAML to the host.
FROM python:3.12-slim-bookworm AS stack-resolver

ARG STACK_NAME=default
WORKDIR /resolver
RUN mkdir -p /resolver/devnaro \
    && pip install --no-cache-dir "PyYAML==6.0.3"
COPY src/devnaro/stack_resolver.py ./devnaro/stack_resolver.py
COPY stacks/ ./stacks/
RUN mkdir -p /out \
    && python -m devnaro.stack_resolver \
        --stack-file "/resolver/stacks/${STACK_NAME}/stack.yaml" \
        --output-dir /out

# The host-side stack selection supplies this value from the validated stack.
# All DevNaro environments use Debian Slim.
FROM ${BASE_IMAGE} AS runtime

ARG USERNAME=devuser
ARG DEVNARO_BOOTSTRAP_UV_VERSION=0.13.7
ARG OH_MY_ZSH_COMMIT=cca3bdfbef8c52ef8939ce7911ff68852b949daa
ARG BASE_IMAGE

RUN mkdir -p /opt/devnaro-config

COPY --from=stack-resolver /out/ /opt/devnaro-config/stack/
RUN test "$(cat /opt/devnaro-config/stack/base-image)" = "$BASE_IMAGE" \
    || { echo "BASE_IMAGE does not match the selected stack definition." >&2; exit 1; }

# Install only runtime requirements for the DevNaro Core.
# Compiler toolchains and development headers are intentionally not part of the final image.
RUN set -eux; \
    . /etc/os-release; \
    test "$ID" = debian; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      bash ca-certificates curl git gnupg nano procps python3 python3-pip socat \
      python3-venv zsh zsh-autosuggestions zsh-syntax-highlighting; \
    install -m 0755 -d /etc/apt/keyrings; \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc; \
    chmod a+r /etc/apt/keyrings/docker.asc; \
    printf 'Types: deb\nURIs: https://download.docker.com/linux/debian\nSuites: %s\nComponents: stable\nArchitectures: %s\nSigned-By: /etc/apt/keyrings/docker.asc\n' "$VERSION_CODENAME" "$(dpkg --print-architecture)" \
      > /etc/apt/sources.list.d/docker.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin

# Install packages declared by the selected stack.
RUN set -eu; \
    cat /opt/devnaro-config/stack/debian-packages.txt \
      | awk '/^[[:space:]]*($|#)/ { next } NF != 1 || $1 !~ /^[A-Za-z0-9+_.-]+$/ { print "Invalid package entry at line " NR ": " $0 > "/dev/stderr"; exit 1 } { if (!seen[$1]++) print $1 }' \
      > /tmp/devnaro-extra-packages; \
    if [ -s /tmp/devnaro-extra-packages ]; then \
      apt-get update; \
      : > /tmp/devnaro-install-packages; \
      while IFS= read -r package; do \
        [ -z "$package" ] && continue; \
        if apt-cache show "$package" 2>/dev/null | grep -Fqx "Package: $package"; then \
          printf '%s\n' "$package" >> /tmp/devnaro-install-packages; \
        else \
          warning="WARNING: Debian package '$package' was not found; skipping."; \
          printf '%s\n' "$warning" >&2; \
        fi; \
      done < /tmp/devnaro-extra-packages; \
      if [ -s /tmp/devnaro-install-packages ]; then \
        xargs -r apt-get install -y --no-install-recommends < /tmp/devnaro-install-packages; \
      fi; \
      rm -f /tmp/devnaro-install-packages; \
    fi; \
    rm -f /tmp/devnaro-extra-packages


# Keep the bootstrap uv/ private to DevNaro; install the stack's uv separately.
RUN python3 -m venv /opt/devnaro-bootstrap-uv \
    && /opt/devnaro-bootstrap-uv/bin/pip install --no-cache-dir "uv==${DEVNARO_BOOTSTRAP_UV_VERSION}"

WORKDIR /opt/devnaro-cli
COPY pyproject.toml uv.lock ./
COPY src/devnaro/ ./src/devnaro/
COPY tests/unit/ ./tests/unit/

RUN python3 -m venv /opt/devnaro-venv \
    && UV_PROJECT_ENVIRONMENT=/opt/devnaro-venv /opt/devnaro-bootstrap-uv/bin/uv sync --locked --all-extras \
    && UV_VERSION="$(cat /opt/devnaro-config/stack/uv-version)" \
    && if [ -n "$UV_VERSION" ]; then \
         python3 -m venv /opt/uv-venv \
         && /opt/uv-venv/bin/pip install --no-cache-dir "uv==${UV_VERSION}" \
         && /opt/uv-venv/bin/uv --version | grep -F "uv ${UV_VERSION}"; \
       fi

ENV PATH="/opt/devnaro-venv/bin:/opt/uv-venv/bin:$PATH"

# DevNaro is a trusted personal development container and runs as root.
# Keep its persistent home isolated from the root home on the host.
RUN mkdir -p "/home/$USERNAME" \
    && chmod 0755 "/home/$USERNAME"

USER root
ENV HOME="/home/${USERNAME}"
WORKDIR /home/${USERNAME}
ENV PATH="/home/${USERNAME}/.local/bin:/opt/devnaro-venv/bin:/opt/uv-venv/bin:$PATH"

RUN git init /home/${USERNAME}/.oh-my-zsh \
    && git -C /home/${USERNAME}/.oh-my-zsh remote add origin https://github.com/ohmyzsh/ohmyzsh.git \
    && git -C /home/${USERNAME}/.oh-my-zsh fetch --depth 1 origin "${OH_MY_ZSH_COMMIT}" \
    && git -C /home/${USERNAME}/.oh-my-zsh checkout --detach FETCH_HEAD \
    && cp /home/${USERNAME}/.oh-my-zsh/templates/zshrc.zsh-template /home/${USERNAME}/.zshrc \
    && sed -i 's/^ZSH_THEME=.*/ZSH_THEME="robbyrussell"/' /home/${USERNAME}/.zshrc \
    && sed -i 's/^plugins=(git)$/plugins=(git docker uv)/' /home/${USERNAME}/.zshrc \
    && AUTOSUGGESTIONS=/usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh \
    && SYNTAX_HIGHLIGHTING=/usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh \
    && printf '\\n# Zsh autosuggestions\\nsource %s\\n' "$AUTOSUGGESTIONS" >> /home/${USERNAME}/.zshrc \
    && printf '\\n# Zsh syntax highlighting\\nsource %s\\n' "$SYNTAX_HIGHLIGHTING" >> /home/${USERNAME}/.zshrc \
    && test "$(git -C /home/${USERNAME}/.oh-my-zsh rev-parse HEAD)" = "${OH_MY_ZSH_COMMIT}" \
    && if [ -x /opt/uv-venv/bin/uv ]; then /opt/uv-venv/bin/uv --version; fi

COPY network_manager/ /opt/network-manager/
COPY src/devnaro/port_forwarding.py /opt/port-forwarding/manager.py
COPY scripts/container/entrypoint.sh /usr/local/bin/devnaro-entrypoint
COPY scripts/container/code /usr/local/bin/code
COPY --from=bridge-builder /devnaro-host-bridge /usr/local/bin/devnaro-host-bridge
COPY --from=bridge-builder /devnaro-status /usr/local/bin/devnaro-status

USER root
RUN mkdir -p /run/devnaro-host \
    && cp /opt/devnaro-config/stack/environment.sh /etc/profile.d/devnaro-stack.sh \
    && chmod 644 /etc/profile.d/devnaro-stack.sh \
    && grep -m1 '^version = ' /opt/devnaro-cli/pyproject.toml | cut -d '"' -f2 > /etc/devnaro-version \
    && test -s /etc/devnaro-version \
    && chmod +x /usr/local/bin/devnaro-entrypoint /usr/local/bin/code \
    && cat >> /etc/zsh/zshrc <<'EOF'

# Restore DevNaro-managed tools after login profiles adjust PATH.
export PATH="/home/${USERNAME}/.local/bin:/opt/devnaro-venv/bin:/opt/uv-venv/bin:${PATH}"
[ -f /etc/profile.d/devnaro-stack.sh ] && source /etc/profile.d/devnaro-stack.sh

function dvn() { devnaro "$@"; }

if [[ -f /tmp/devnaro-welcome-pending ]]; then
    rm -f /tmp/devnaro-welcome-pending
    devnaro welcome
fi
EOF

USER root
ENTRYPOINT ["/usr/local/bin/devnaro-entrypoint"]
CMD ["sleep", "infinity"]
