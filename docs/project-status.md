# DevBox — Project Status and Roadmap

> Snapshot recorded on 2026-11-12.
> PRs #21, #22 and the Stack-aware image architecture work have been merged into `main`.
> This is a progress snapshot; check the repository and CI for live state.

## Current state

DevBox currently provides one Alpine-based development container with a host CLI, container CLI (`dm`), persistent home, mounted workspace, Docker integration, Network Manager and VS Code host bridge.

The image is now stack-aware: a declarative stack definition is validated before the runtime image is built, and its normalized inputs control additional Alpine packages, supported development tools and environment variables. The default stack preserves the existing environment.

Multi-DevBox is still future work. Compose, container naming, hostname, home volume and several host integrations still assume a single instance.

## Implemented

- Alpine 3.22 development image and Python 3.12 runtime for the DevBox CLI.
- Non-root container user, Zsh/Oh My Zsh setup, persistent home and mounted workspace.
- Host CLI lifecycle: start, stop, restart, recreate, recreate-all and clean.
- Container CLI (`dm`) built with Typer and Rich.
- Docker CLI/Compose integration and Network Manager.
- VS Code host bridge and terminal integration.
- Configurable port override file and shell completions.
- Alpine package search and package manifest operations: `dm tools search/add/remove/list`.
- Build-time validation and warning-and-skip behavior for unavailable optional Alpine packages.
- Shared host Compose wrapper (`scripts/host/compose.sh`) and terminal helpers (`scripts/host/ui.sh`).
- Stack Definition schema v1 at `stacks/<name>/stack.yaml`.
- Python Stack Resolver with safe YAML loading, duplicate-key rejection, strict validation and normalized build artifacts.
- Generic Dockerfile build flow that consumes resolver output; YAML parsing stays outside the runtime image stage.
- Stack-controlled additional Alpine packages, Terraform and uv versions, and environment variables.
- Separate DevBox bootstrap uv and stack-provided uv installations.
- Architecture-aware Terraform installation for amd64 and arm64.
- Unit tests and CI validation for Python, repository checks and Docker image build.

## Partially implemented / current limitations

- Only `default` stack is currently defined; stack selection is supplied through the `STACK_NAME` build argument/environment.
- Stack schema v1 supports only `terraform` and `uv` as development tools.
- Alpine package manifest `docker/packages.txt` remains global rather than per environment.
- Tool metadata and image-provided-tool knowledge are not yet exposed as a complete normalized inventory in `dm info`.
- Host CLI and Compose still assume one fixed DevBox instance, service, container name, hostname and home volume.
- Network Manager and VS Code bridge are not yet multi-instance aware.

## Phase 1 — Consolidation and maintenance

Status: completed and merged into `main` (PR #22).

- Consolidated host-side Compose arguments in `scripts/host/compose.sh`.
- Added shared terminal helpers in `scripts/host/ui.sh`.
- Fixed workflow branch filtering and package lookup output.
- Corrected README package-manifest documentation.
- Consolidated Alpine repository package-index loading.
- Expanded package manifest validation tests.

## Phase 2 — Stack-aware image architecture

Status: completed and merged into `main`.

Decisions and delivered behavior:

- One generic Dockerfile builds DevBox Core plus a selected stack.
- One generic Compose definition remains responsible for orchestration.
- Stacks are declarative YAML; they do not contain Dockerfiles, Compose files or arbitrary shell commands.
- The Stack Resolver validates definitions before the runtime image build and emits normalized build inputs.
- Stack tools are installed at image-build time for reproducibility.
- Core dependencies remain separate from user development tools.
- The existing environment is preserved as the `default` stack.
- Multi-DevBox was intentionally kept out of this phase.

Validation completed:
- Resolver unit tests and the full Python test suite passed.
- Local Docker image build and DevBox lifecycle checks passed.
- The default stack's Terraform, uv and Python versions were checked in the container.
- Package management and Compose configuration checks passed.
- GitHub Actions passed for Docker image build, repository validation and Python tests.

## Phase 3 — Multi-DevBox architecture

Status: next phase; design first, implementation after decisions are agreed.

Goal: allow multiple named DevBox environments to coexist without breaking the current single-instance workflow.

Proposed work sequence:

1. Define the environment model and registry: identity, stack association, workspace, configuration and lifecycle state.
2. Define default-environment selection and how the active environment is identified in the prompt and CLI.
3. Design instance-specific Compose project/container/hostname/home-volume naming and port allocation.
4. Define how package customization and stack selection work per environment.
5. Plan multi-instance behavior for VS Code bridge, Network Manager, diagnostics and selective cleanup.
6. Implement incrementally, preserving backward compatibility for the existing default DevBox.

Do not start implementation until the registry, naming and lifecycle contracts are agreed.

## Architectural guardrails

- Avoid broad rewrites and speculative abstractions.
- Keep stack definitions declarative; no arbitrary shell execution.
- Separate DevBox Core dependencies from user development tools.
- Keep image builds reproducible and install stack tools at build time.
- Preserve the existing single-instance workflow during the Multi-DevBox transition.
- Create directories and abstractions only when they are needed.
- Run focused tests after each change, followed by Python, shell, Compose and Docker validation.
- Do not merge pull requests unless the user explicitly asks.
