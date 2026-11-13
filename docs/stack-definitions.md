# Stack Definition Contract

## Purpose

A stack describes the development environment inputs that DevBox uses when
building its image. It does not define Docker build steps, container
orchestration, arbitrary shell commands or host integration.

DevBox validates the selected YAML definition before building the runtime
image.

## Current stack

The current implementation provides one stack:

| Stack | Base image | Stack-managed tools |
| --- | --- | --- |
| `default` | Debian Trixie Slim | uv 0.13.7 |

The `default` stack is selected implicitly by the current host Compose
configuration and Docker build argument. Explicit selection among multiple
stacks is not part of the current implementation.

The stack definition is stored at:

```text
stacks/<stack-name>/stack.yaml
```

The directory name and the `name` field must match.

## Base image policy

**Debian Slim is the only supported distribution throughout the project.**
All Docker build stages and the runtime image use Debian-based images. The
current runtime uses `debian:trixie-slim`.

Use APT for system packages. Do not add compilers, headers or convenience tools
to DevBox Core unless they are required by its runtime functionality. Build-only
dependencies must be removed in the same image layer or kept in a separate
build stage.

The Dockerfile installs Docker CLI and Compose from Docker's official APT
repository. The non-root developer account, Docker socket group, Zsh and its
plugins are configured using Debian tooling and package paths.

The `dm tools search/add/remove/list` commands use the Debian APT package
indexes included in the image. The package manifest remains host-backed:
changes take effect after `devbox recreate`, not in the running container.

## Version policy

The current stack-managed tool installer supports **uv** only. The current
stack pins uv to an exact version (`0.13.7`).

The schema accepts `version` or `channel` declarations, but channel values
are only syntactically validated today. Channel-to-version resolution and
tool-specific installers are not implemented. Use exact versions for the
currently supported tool.

The DevBox bootstrap uv is a separate internal Core dependency. It is used to
prepare the DevBox CLI environment and is not the stack-managed uv installation.

## Definition schema

Schema version 2 supports the following fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Must be `2`. |
| `name` | Stack identifier; must match its directory. |
| `description` | Short human-readable description. |
| `base.distribution` | Must be `debian`. |
| `base.version` | Explicit Debian release codename/version. |
| `packages.debian` | Optional list of additional Debian APT packages. |
| `tools.<name>.version` | Exact tool version; mutually exclusive with `channel`. |
| `tools.<name>.channel` | Syntactically accepted release channel (`lts` or `stable`); resolution is not implemented. |
| `environment` | Environment variables available in the container. |

The selected base is normalized to the official Debian Slim image:
`debian:<version>-slim`. The Docker build accepts this exact reference through
the `BASE_IMAGE` build argument and checks it against the stack resolver output.
The host Compose configuration currently supplies the Debian Trixie Slim
default. Package lists are Debian-only; empty or omitted lists add no packages.

The schema remains strict: unknown fields are rejected, tool installers are
owned by DevBox, and stack files cannot execute arbitrary shell commands.

## Example

```yaml
schema_version: 2

name: default
description: DevBox default development environment.

base:
  distribution: debian
  version: "trixie"

packages:
  debian: []

tools:
  uv:
    version: "0.13.7"

environment: {}
```

## Core and stack separation

The existing Core dependencies and integrations remain available in the
runtime image. This includes the DevBox CLI runtime, shell, Docker CLI
integration, Network Manager and host bridge behavior.

The bootstrap uv remains an internal Core dependency. The stack-provided uv is
installed separately and is controlled by the selected stack definition.

Terraform is not part of DevBox Core or the currently supported stack-managed
tools.

## Reproducibility

The selected stack is validated and normalized during image build. Exact tool
versions are installed as declared. An existing image does not silently update
its tools; rebuild the image to apply changes.

## Explicit non-goals

- Multiple curated stacks or mandatory interactive stack selection.
- Arbitrary shell commands or custom installer scripts in stack definitions.
- Stack inheritance or composition.
- Docker services, ports, volumes or networks in stack definitions.
- Secrets and host-specific configuration in stack definitions.
- Runtime installation of stack tools.
- Silent in-place upgrades of tools inside an existing image.
- Terraform installation or support.
