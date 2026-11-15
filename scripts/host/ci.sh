#!/usr/bin/env bash
set -Eeuo pipefail

ACT_VERSION="0.2.89"
ACT_RELEASE="https://github.com/nektos/act/releases/download/v${ACT_VERSION}"

usage() {
    cat <<'EOF'
Run the DevBox GitHub Actions workflow locally.

Usage:
  devbox ci                 Run all jobs in devbox-validation.yml
  devbox ci --list          List workflows and jobs
  devbox ci -j python-tests Run one job
  devbox ci --dry-run        Show the execution plan without running jobs
  devbox ci --help          Show act options

Additional arguments are passed directly to act.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
    printf 'Docker CLI is required to run local GitHub Actions.\n' >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    printf 'Docker Engine is not reachable. Start Docker and try again.\n' >&2
    exit 1
fi

install_act() {
    local architecture asset checksum temp_dir
    case "$(uname -m)" in
        x86_64|amd64)
            architecture="x86_64"
            checksum="0191d6f1f3b716b5c55820032605d05fc3c1cdbf581ebeff655019e5dd1524c0"
            ;;
        aarch64|arm64)
            architecture="arm64"
            checksum="daa8679ba9615a74d2d0cec321dc593f21948a2a11bb65862b063d8b930f4bcb"
            ;;
        *)
            printf 'Unsupported architecture for automatic act installation: %s\n' "$(uname -m)" >&2
            exit 1
            ;;
    esac

    for dependency in curl tar sha256sum install; do
        if ! command -v "$dependency" >/dev/null 2>&1; then
            printf 'Missing required command: %s\n' "$dependency" >&2
            exit 1
        fi
    done

    asset="act_Linux_${architecture}.tar.gz"
    temp_dir="$(mktemp -d)"
    trap 'rm -rf "$temp_dir"' RETURN

    printf 'Installing act v%s for Linux/%s...\n' "$ACT_VERSION" "$architecture"
    curl --fail --location --silent --show-error \
        "${ACT_RELEASE}/${asset}" -o "$temp_dir/act.tar.gz"
    printf '%s  %s\n' "$checksum" "$temp_dir/act.tar.gz" | sha256sum --check --status

    tar -xzf "$temp_dir/act.tar.gz" -C "$temp_dir" act
    install -d "$HOME/.local/bin"
    install -m 0755 "$temp_dir/act" "$HOME/.local/bin/act"
    printf 'Installed: %s\n' "$HOME/.local/bin/act"
}

if ! command -v act >/dev/null 2>&1; then
    install_act
    export PATH="$HOME/.local/bin:$PATH"
fi

REPOSITORY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKFLOW="$REPOSITORY_DIR/.github/workflows/devbox-validation.yml"

if [[ ! -f "$WORKFLOW" ]]; then
    printf 'Workflow not found: %s\n' "$WORKFLOW" >&2
    exit 1
fi

# Run on the host: Docker must be able to mount the real repository path.
# The full runner image provides the Ubuntu tools used by this workflow.
exec act push \
    --workflows "$WORKFLOW" \
    --platform ubuntu-latest=catthehacker/ubuntu:act-latest \
    --container-daemon-socket /var/run/docker.sock \
    "$@"
