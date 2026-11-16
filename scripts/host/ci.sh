#!/usr/bin/env bash
set -Eeuo pipefail

ACT_VERSION="0.2.97"
ACT_RELEASE="https://github.com/nektos/act/releases/download/v${ACT_VERSION}"

usage() {
    cat <<'EOF'
Run the DevNaro GitHub Actions workflow locally.

Usage:
  devnaro ci                 Run all jobs in devnaro-validation.yml
  devnaro ci --list          List workflows and jobs
  devnaro ci -j python-tests Run one job
  devnaro ci --dry-run        Show the execution plan without running jobs
  devnaro ci --help          Show act options

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
            checksum="67b4976a56f33ea7870b798912e738ec44eef38e7578ae7b532f2def1c73a5ad"
            ;;
        aarch64|arm64)
            architecture="arm64"
            checksum="44d48e3d4a6409053fdec6fc6518322467d79a2d5be8f72c021b0421e2ac113d"
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
WORKFLOW="$REPOSITORY_DIR/.github/workflows/devnaro-validation.yml"

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
