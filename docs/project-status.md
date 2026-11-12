# DevBox — Project Status and Roadmap

> Snapshot recorded on 2026-11-12.
> PR #21 and PR #22 have been merged into `main` by the user.
> This document is a progress snapshot, not a substitute for checking the current code and CI.

## Current state

The current DevBox supports a single Alpine-based development container with a host CLI, container CLI (`dm`), persistent home, mounted workspace, Docker integration, Network Manager and VS Code host bridge.

PR #21 added Alpine package search and package manifest management.

PR #22 consolidated host-side Compose invocation and shared UI helpers, fixed maintenance issues, and consolidated Alpine repository package-index loading. The user confirmed that PR #22 was merged. Its final CI status was not independently re-checked in this snapshot.

## Implemented

- Alpine 3.22-based development container.
- Python 3.12, uv, Terraform, Docker CLI and Compose.
- Non-root container user, Zsh/Oh My Zsh setup.
- Persistent home volume and host-mounted workspace.
- Host CLI lifecycle: start, stop, restart, recreate, recreate-all, clean.
- Host status, info, logs, networks, doctor and machine workspace configuration.
- Container CLI (`dm`) built with Typer and Rich.
- Network Manager for discovering/reconciling eligible Docker networks.
- VS Code host bridge and terminal integration.
- Configurable port override file.
- Shell completions.
- Alpine package search and package manifest operations: `dm tools search/add/remove/list`.
- Build-time validation and warnings for unavailable optional Alpine packages.
- Shared host Compose wrapper in `scripts/host/compose.sh`.
- Shared stop/clean terminal helpers in `scripts/host/ui.sh`.
- Consolidated Alpine repository package-index loading.
- Unit tests and CI validation workflow.

## Partially implemented

- Tool inventory exists in `dm info`, but does not yet provide a complete normalized inventory with reliable versions, categories, origins and future stack associations.
- Package management works, but the manifest is global (`docker/packages.txt`), not per environment.
- Host CLI and Docker Compose operations assume one fixed DevBox instance.
- Tool metadata and image-provided-tool knowledge are spread across the Dockerfile and Python CLI.
- The Dockerfile still combines Core runtime setup with stack-specific tools such as Terraform and uv.
- Docker Compose still assumes a fixed service, container name, hostname and home volume.

## Not implemented

- Multi-DevBox registry and named environments.
- Default environment selection and environment identity in the prompt.
- Stack resolver and build-input generation.
- Generic stack-aware image build.
- Generic multi-instance orchestration.
- Per-environment package manifests and customization.
- Per-instance port allocation and isolation.
- Multi-instance VS Code bridge and Network Manager behavior.
- Complete environment-aware diagnostics and selective cleanup.

## Phase 1 — Consolidation and maintenance

Status: merged into `main` via PR #22.

Completed:
- Added `scripts/host/compose.sh` as the single source for DevBox Compose project arguments; host CLI, lifecycle scripts and Makefile delegate to it.
- Added `scripts/host/ui.sh` for terminal helpers shared by stop and clean.
- Fixed the malformed workflow branch filter.
- Fixed the literal escaped newline in the package lookup error.
- Corrected the README package manifest location and documented shared host helpers.
- Consolidated Alpine repository index loading so search and availability checks use one shared path.
- Added positive and negative package-name validation test cases.

Deliberately not added:
- A separate tool catalog where only one consumer exists.
- A Python runtime dependency for Docker build-time manifest validation.
- Broad host UI refactoring where startup UI remains unique.

## Phase 2 — Stack-aware image architecture

Status: started on branch `feat/stack-definition-foundation`.

Architectural decisions:
- Maintain one generic Dockerfile for the shared DevBox Core plus a selected stack.
- Maintain one generic Compose definition for orchestration; stack definitions do not contain Compose files.
- Represent stacks declaratively in YAML.
- Resolve and validate stack definitions before the Docker build; do not put YAML interpretation inside the Dockerfile.
- Install stack tools at image-build time for reproducibility.
- Do not allow arbitrary shell commands or custom installer scripts in stack definitions.
- Keep the current environment available as the `default` stack during migration.
- Do not implement Multi-DevBox yet.

Initial schema contract:
- `schema_version`: definition format version.
- `name` and `description`: stack identity and summary.
- `packages.alpine`: additional Alpine packages.
- `tools`: supported tool identifiers and pinned versions.
- `environment`: string-valued environment variables.

Initial implementation:
- Added `stacks/default/stack.yaml` with the current Terraform and uv versions.
- Added `docs/stack-definitions.md` documenting schema version 1, supported tool identifiers, validation expectations and explicit non-goals.
- These files are currently descriptive inputs only. The existing Dockerfile remains authoritative until resolver and build integration are implemented and tested.

Next steps:
1. Implement stack definition parsing and strict validation in the Python CLI.
2. Add tests for valid definitions, invalid fields, unsupported tools, invalid package names and directory/name mismatch.
3. Generate normalized build inputs from the resolved stack.
4. Refactor the Dockerfile to consume those inputs while preserving the current default image behavior.
5. Make Compose build configuration generic without introducing multi-instance behavior yet.
6. Run the full CI and compare the resulting default image behavior against the current environment.

## Architectural guardrails

- Avoid broad rewrites or speculative abstractions.
- Reuse code where multiple real consumers exist.
- Keep Docker build independent of unnecessary runtime dependencies.
- Preserve current single-instance behavior until stack-aware image building is complete.
- Keep stack definitions declarative; no arbitrary shell execution.
- Separate DevBox Core dependencies from user development tools.
- Do not create directories and abstractions ahead of their first real use.
- Run focused tests after each change, then complete Python, shell, Compose and Docker CI validation.
- Do not merge pull requests unless the user explicitly asks.

## Multi-DevBox — future scope

- Registry and named environments.
- Default environment selection and environment identity in the prompt.
- Per-environment package manifests and customization.
- Per-instance port allocation and isolation.
- Multi-instance VS Code bridge and Network Manager behavior.
- Environment-aware diagnostics and selective cleanup.
