# DevBox — Project Status and Roadmap

> Snapshot recorded on 2026-11-12 after merging PR #21.
> Audited base: `main` at commit `8d9c849209336477a07bfbf3ace91276f521fbf4`.
> This document is a progress snapshot, not a substitute for checking the current code and CI.

## Current state

PR #21 (container-only Alpine package search and package manifest management) is merged.
The merge commit passed all three GitHub Actions jobs:
- Python tests: 58 passed.
- Repository validation: passed (shell syntax and Docker Compose configuration).
- Docker image build and container smoke tests: passed.

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
- Unit tests and CI validation workflow.

## Partially implemented

- Tool inventory exists in `dm info`, but does not yet provide a complete normalized inventory with reliable versions, categories, origins and future stack associations.
- Package management works, but the manifest is global (`docker/packages.txt`), not per environment.
- Host CLI and Docker Compose operations assume one fixed DevBox instance.
- Tool metadata and image-provided-tool knowledge are spread across the Dockerfile and Python CLI.
- Alpine manifest entry validation is implemented in both Python and Docker build logic; their behavior needs compatibility coverage.
- Alpine package discovery has overlapping index-fetching/parsing flows that may be consolidated.

## Not implemented

- Multi-DevBox registry and named environments.
- Default environment selection and environment identity in the prompt.
- Declarative stack catalog.
- Per-environment package manifests and customization.
- Per-instance port allocation and isolation.
- Multi-instance VS Code bridge and Network Manager behavior.
- Complete environment-aware diagnostics and selective cleanup.

## Phase 1 — Consolidation and maintenance

Work on a dedicated branch before starting Multi-DevBox.

1. Fix confirmed maintenance defects:
   - Malformed branch entry in `.github/workflows/devbox-validation.yml` (literal escaped newline in the branch list).
   - Incorrect escaped newline in the `dm tools add` error/help output, if still present in the current source.
   - README repository tree/path inaccuracies.
2. Centralize host-side Docker Compose invocation and common project path/config resolution, without changing behavior.
3. Reduce duplicated tool metadata and image-provided-tool checks through a small, authoritative catalog where it is genuinely shared.
4. Keep Python and Docker build manifest validation compatible; add tests for the accepted/rejected input contract rather than introducing an unnecessary runtime dependency.
5. Consolidate Alpine repository index retrieval/parsing where it removes real duplication.
6. Review GitHub Actions versions and update deprecated Node 20 action references where safe.

## Architectural guardrails

- Avoid a broad rewrite or speculative abstractions.
- Keep each responsibility implemented once where multiple callers genuinely share it.
- Do not make Docker build depend on the Python CLI merely to remove a small amount of duplicated validation.
- Preserve current single-instance behavior during Phase 1.
- Create directories and abstractions only when required by an implemented feature.
- Run focused tests after each change, then the complete Python, shell, Compose and Docker CI validation.
- Multi-DevBox implementation must not begin until Phase 1 changes are reviewed and merged.

## Audit notes

The audit found repeated Compose argument construction in host scripts and Makefile; repeated terminal presentation helpers in host scripts; tool knowledge split between the Dockerfile and Python CLI; and separate but related package-manifest validation paths. These are candidates for targeted consolidation, not proof that every similar line must be abstracted.

No source changes were made as part of the initial audit. Phase 1 work is tracked separately from this snapshot.
