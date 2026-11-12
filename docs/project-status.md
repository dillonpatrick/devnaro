# DevBox — Project Status and Roadmap

> Snapshot recorded on 2026-11-12.
> PRs #21, #22 and Stack-aware image architecture have been merged into `main`.
> Curated development stacks are being designed on `feat/curated-development-stacks`.
> This is a progress snapshot; check the repository and CI for live state.

## Current state

DevBox currently has a single Alpine-based development container with a host
CLI, container CLI (`dm`), persistent home, mounted workspace, Docker
integration, Network Manager and VS Code host bridge.

The image build is stack-aware, but the current implementation still has one
`default` stack, supports only Terraform and uv as stack tools, and assumes
Alpine in the runtime Dockerfile. The curated-stacks work will remove those
limitations before Multi-DevBox begins.

## Implemented

- Alpine 3.22 image and Python 3.12 runtime for the DevBox CLI.
- Non-root user, Zsh/Oh My Zsh, persistent home and mounted workspace.
- Host CLI lifecycle: start, stop, restart, recreate, recreate-all and clean.
- Container CLI (`dm`) built with Typer and Rich.
- Docker CLI/Compose integration and Network Manager.
- VS Code host bridge and terminal integration.
- Configurable port override file and shell completions.
- Alpine package search and package manifest operations: `dm tools search/add/remove/list`.
- Build-time validation and warning-and-skip behavior for unavailable optional Alpine packages.
- Shared host Compose wrapper and terminal helpers.
- Stack Definition schema v2 and Python Stack Resolver with safe YAML loading,
  duplicate-key rejection, strict validation and normalized build artifacts.
- Stack-controlled Alpine/Debian packages, base image selection, tool versions
  or release channels, and environment.
- Separate DevBox bootstrap uv and stack-provided uv installations.
- Unit tests and CI validation for Python, repository checks and Docker build.

## Current limitations

- A `default` stack still exists and is currently selected implicitly.
- Only `terraform` and `uv` are supported stack tools.
- Stack package declarations support Alpine and Debian, but the Dockerfile
  runtime build still installs only Alpine packages.
- The runtime Dockerfile and Core package installation assume Alpine.
- Tool versions are pinned manually; release-channel resolution is not implemented.
- `docker/packages.txt` remains a global user package manifest.
- Host CLI, Compose, Network Manager and VS Code bridge still assume one instance.

## Phase 1 — Consolidation and maintenance

Status: completed and merged into `main` (PR #22).

- Consolidated host-side Compose arguments and terminal helpers.
- Fixed workflow branch filtering and package lookup output.
- Corrected README package-manifest documentation.
- Consolidated Alpine repository package-index loading.
- Expanded package manifest validation tests.

## Phase 2 — Stack-aware image architecture

Status: completed and merged into `main`.

- Generic Dockerfile and Compose definition.
- Declarative stack YAML and strict Stack Resolver.
- Normalized build inputs, with YAML parsing outside the runtime image stage.
- Build-time stack tool installation and separation of Core dependencies.
- Existing environment retained as `default` during the initial migration.

## Phase 2.5 — Curated development stacks

Status: design agreed; schema v2 implemented on
`feat/curated-development-stacks`. Multi-distribution Core installation and
stack tool installers remain pending.

Agreed decisions:

- Remove the `default` stack; users must select a stack.
- Initial stacks: Python, Node.js, DevOps and Go.
- Keep all existing Core dependencies.
- Remove Terraform from Core/default installation; Terraform belongs to DevOps.
- Allow each stack to select Alpine or Debian while retaining the same Core
  capabilities.
- Use Debian for DevOps to improve compatibility with official cloud CLIs that
  may not support Alpine/musl equivalently. Keep Alpine for Python, Node.js and
  Go where practical.
- Prefer official LTS channels. Where no LTS exists, use the newest stable,
  upstream-supported release.
- Resolve channels to exact versions during image build and record the
  resolved versions. Existing images do not update themselves.

Planned initial toolsets:

- Python: Python, uv, pytest, Ruff, mypy.
- Node.js: Node.js LTS, npm, Yarn, TypeScript, ESLint, Prettier.
- DevOps: AWS CLI, Azure CLI, Google Cloud CLI, Terraform, Ansible, kubectl,
  Helm.
- Go: Go, golangci-lint, Delve, Air.

Implementation sequence:

1. [x] Revise stack schema for base distribution, distribution-specific
   packages and release channel declarations.
2. Make Core installation work on Alpine and Debian without duplicating Core
   behavior.
3. Add supported installers and version resolvers for the curated toolsets.
4. Add the four stack definitions and remove the implicit default selection.
5. Update CLI/Compose startup to require an explicit stack selection.
6. Update `dm info`, tests, CI and user documentation.

## Phase 3 — Multi-DevBox architecture

Status: deferred until curated stacks are implemented and validated.

Goal: allow multiple named DevBox environments to coexist.

Proposed work sequence:

1. Define the environment registry: identity, stack association, workspace,
   configuration and lifecycle state.
2. Define environment selection and active-environment display in the CLI.
3. Design instance-specific Compose project/container/hostname/home-volume
   naming and port allocation.
4. Plan multi-instance behavior for VS Code bridge, Network Manager,
   diagnostics and selective cleanup.
5. Implement incrementally, preserving a simple single-environment workflow.

## Architectural guardrails

- Keep stack definitions declarative; no arbitrary shell execution.
- Separate Core dependencies from user development tools.
- Resolve moving release channels to exact versions at build time.
- Preserve the same Core capabilities across supported base distributions.
- Avoid broad rewrites and speculative abstractions.
- Create directories and abstractions only when needed.
- Run focused tests, then Python, shell, Compose and Docker validation.
- Keep this document updated as implementation progresses.
- Do not merge pull requests unless the user explicitly asks.
