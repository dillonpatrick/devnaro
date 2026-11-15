# Stack Definition Contract

## Purpose

A stack describes the development tools and environment-specific configuration
that DevBox includes in an image. It does not define Docker build steps,
container orchestration, arbitrary shell commands or host integration.

DevBox validates each YAML definition before building the runtime image.

## Available stacks

There is no default development stack in the curated-stack design. Users will
select one of the available stacks when creating an environment.

Initial curated stacks:

| Stack | Base image | Main tools |
| --- | --- | --- |
| `python` | Debian Trixie Slim | Python, uv, pytest, Ruff, mypy |
| `nodejs` | Debian Trixie Slim | Node.js LTS, npm, Yarn, TypeScript, ESLint, Prettier |
| `devops` | Debian Trixie Slim | AWS CLI, Azure CLI, Google Cloud CLI, Ansible, kubectl, Helm |
| `go` | Debian Trixie Slim | Go, golangci-lint, Delve, Air |

The exact package and tool declarations are maintained in each stack's
`stack.yaml`. This table is the curated baseline, not a substitute for those
definitions.

## Base image policy

**Debian Slim is the only supported distribution throughout the project.**
All Docker build stages and all runtime stacks use Debian-based images. Runtime
stacks use the official Debian Slim variant (for example,
`debian:trixie-slim`).

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

Stack tools should stay on the newest supported release channel:

- Use the official LTS channel when the upstream project provides one.
- If there is no LTS channel, use the newest stable release that is still
  supported upstream. Do not label a release LTS when the project does not.
- Avoid alpha, beta, release-candidate and other prerelease versions.

Examples:
- Node.js: latest official LTS line.
- Python: latest stable supported release; Python uses feature, bugfix,
  security and end-of-life phases rather than an LTS channel.
- Go: latest stable supported release; Go support follows its release policy,
  not an LTS designation.
- Terraform and cloud CLIs: latest stable supported release according to each
  vendor's release/support policy.

Stack definitions may declare either an exact version or a supported channel.
The schema accepts `lts` and `stable`; whether a particular tool supports a
channel is validated by its tool-specific resolver. During image build, the
resolver/build tooling resolves a channel to an exact version, records that
version in generated build metadata, and installs that exact version. The
resulting image is immutable: new upstream releases are picked up on the next
image rebuild, not silently inside an already-created container.

Build logs and `dm info` should expose both the requested channel and the
resolved version. Resolution must fail clearly if an upstream version cannot
be determined; it must not silently install an arbitrary version.

## Stack definition location

Each stack is stored at:

```text
stacks/<stack-name>/stack.yaml
```

The directory name and the `name` field must match.

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
| `tools.<name>.channel` | Release channel: `lts` or `stable`; mutually exclusive with `version`. |
| `environment` | Environment variables available in the container. |

The selected base is normalized to the official Debian Slim image:
`debian:<version>-slim`. The Docker build accepts this exact reference through
the `BASE_IMAGE` build argument and checks it against the stack resolver output.
The host Compose configuration currently supplies the same Debian Trixie Slim
default. Package lists are Debian-only; empty or omitted lists add no packages.

The schema remains strict: unknown fields are rejected, tool installers are
owned by DevBox, and stack files cannot execute arbitrary shell commands.
A tool-specific resolver must reject channels that the upstream tool does not
actually provide.

## Example

```yaml
schema_version: 2

name: python
description: Python development environment.

base:
  distribution: debian
  version: "trixie"

packages:
  debian:
    - git
    - jq

tools:
  uv:
    channel: stable

environment: {}
```

## Core and stack separation

The existing Core dependencies and integrations remain available in every
stack. This includes the DevBox CLI runtime, shell, Docker CLI integration,
Network Manager and host bridge behavior.

Terraform is not a Core dependency; it belongs only to the DevOps stack. The
DevBox bootstrap uv remains an internal Core dependency; a user-facing uv
installation belongs only to the Python stack.

## Reproducibility

The selected stack is resolved during image build. Channel names such as
`lts` and `stable` are resolved to exact tool versions and recorded in the
image metadata. Rebuilding later may resolve newer versions, while an existing
image remains unchanged.

## Explicit non-goals

- Arbitrary shell commands or custom installer scripts in stack definitions.
- Stack inheritance or composition.
- Docker services, ports, volumes or networks in stack definitions.
- Secrets and host-specific configuration in stack definitions.
- Runtime installation of stack tools.
- Silent in-place upgrades of tools inside an existing image.
