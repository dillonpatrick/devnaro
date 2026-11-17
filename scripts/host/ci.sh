#!/usr/bin/env bash
set -Eeuo pipefail

ACT_VERSION="0.2.97"
ACT_RELEASE="https://github.com/nektos/act/releases/download/v${ACT_VERSION}"
GITHUB_API_URL="https://api.github.com"

usage() {
    cat <<'EOF'
Run the DevNaro GitHub Actions workflow locally.

Usage:
  devnaro ci                 Run all jobs in devnaro-validation.yml
  devnaro ci --list          List workflows and jobs
  devnaro ci -j python-tests Run one job
  devnaro ci --dry-run       Show the execution plan without running jobs
  devnaro ci --help          Show act options

Optional GitHub reporting:
  DEVNARO_GITHUB_TOKEN       GitHub App installation token with Checks: write
  DEVNARO_GITHUB_REPOSITORY  Override owner/repository detection

When a token is configured, a check run is created and updated on the current
commit. The act logs remain local; only the final result and summary are sent.
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

github_token="${DEVNARO_GITHUB_TOKEN:-${GH_TOKEN:-${GITHUB_TOKEN:-}}}"
check_run_id=""
check_repository="${DEVNARO_GITHUB_REPOSITORY:-}"

resolve_github_repository() {
    local remote
    remote="$(git -C "$REPOSITORY_DIR" remote get-url origin 2>/dev/null || true)"

    case "$remote" in
        https://github.com/*)
            check_repository="${remote#https://github.com/}"
            ;;
        git@github.com:*)
            check_repository="${remote#git@github.com:}"
            ;;
        ssh://git@github.com/*)
            check_repository="${remote#ssh://git@github.com/}"
            ;;
    esac

    check_repository="${check_repository%.git}"
}

publish_check_start() {
    local head_sha response_file
    if [[ -z "$github_token" ]]; then
        printf 'GitHub reporting skipped (set DEVNARO_GITHUB_TOKEN to enable it).\n'
        return 0
    fi

    if ! command -v curl >/dev/null 2>&1; then
        printf 'GitHub reporting skipped: curl is not installed.\n' >&2
        return 0
    fi

    if [[ -z "$check_repository" ]]; then
        resolve_github_repository
    fi

    if [[ ! "$check_repository" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
        printf 'GitHub reporting skipped: unable to determine owner/repository.\n' >&2
        return 0
    fi

    if ! head_sha="$(git -C "$REPOSITORY_DIR" rev-parse HEAD 2>/dev/null)"; then
        printf 'GitHub reporting skipped: current commit could not be determined.\n' >&2
        return 0
    fi

    response_file="$(mktemp)"
    if curl --fail --silent --show-error \
        --request POST \
        --url "${GITHUB_API_URL}/repos/${check_repository}/check-runs" \
        --header "Accept: application/vnd.github+json" \
        --header "Authorization: Bearer ${github_token}" \
        --header "X-GitHub-Api-Version: 2022-11-28" \
        --header "Content-Type: application/json" \
        --data "{\"name\":\"DevNaro Local CI (act)\",\"head_sha\":\"$head_sha\",\"status\":\"in_progress\",\"output\":{\"title\":\"Local validation started\",\"summary\":\"DevNaro is running the repository workflow locally with act. Full logs remain in the local terminal.\"}}" \
        --output "$response_file"; then
        check_run_id="$(sed -n 's/^[[:space:]]*"id":[[:space:]]*\([0-9][0-9]*\),.*/\1/p' "$response_file" | head -n 1)"
    fi
    rm -f "$response_file"

    if [[ -n "$check_run_id" ]]; then
        printf 'GitHub Check created: https://github.com/%s/commit/%s/checks\n' "$check_repository" "$head_sha"
    else
        printf 'GitHub reporting could not create a Check. Verify the GitHub App token and Checks: write permission; continuing with local CI.\n' >&2
    fi
}

publish_check_result() {
    local conclusion="$1"
    local duration="$2"
    local summary="$3"

    [[ -n "$check_run_id" ]] || return 0

    if ! curl --fail --silent --show-error \
        --request PATCH \
        --url "${GITHUB_API_URL}/repos/${check_repository}/check-runs/${check_run_id}" \
        --header "Accept: application/vnd.github+json" \
        --header "Authorization: Bearer ${github_token}" \
        --header "X-GitHub-Api-Version: 2022-11-28" \
        --header "Content-Type: application/json" \
        --data "{\"status\":\"completed\",\"conclusion\":\"$conclusion\",\"output\":{\"title\":\"Local CI $conclusion\",\"summary\":\"$summary\\n\\nDuration: ${duration}s. Execution: local via act. Full logs remain in the local terminal.\"}}"; then
        printf 'Warning: unable to update the GitHub Check result.\n' >&2
    fi
}

publish_check_start

started_at="$(date +%s)"
act_status=0

# Run on the host: Docker must be able to mount the real repository path.
# The full runner image provides the Ubuntu tools used by this workflow.
act push \
    --workflows "$WORKFLOW" \
    --platform ubuntu-latest=catthehacker/ubuntu:act-latest \
    --container-daemon-socket /var/run/docker.sock \
    "$@" || act_status=$?

finished_at="$(date +%s)"
duration=$((finished_at - started_at))

if [[ "$act_status" -eq 0 ]]; then
    publish_check_result "success" "$duration" "All selected act jobs completed successfully."
else
    publish_check_result "failure" "$duration" "act exited with status $act_status. Inspect the local terminal output for the failing step and full logs."
fi

exit "$act_status"
