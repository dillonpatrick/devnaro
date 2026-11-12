# Stack Definition Contract

## Purpose

A stack describes the development tools and environment-specific configuration
that DevBox should include in an image. It does not define Docker build steps,
container orchestration, arbitrary shell commands or host integration.

The contract is versioned. DevBox resolves and validates the YAML before the
runtime image is built.

## Available stacks

There is no default development stack. Users must choose one of the available
stacks when creating an environment.

Initial curated stacks:

| Stack | Base image | Main tools |
| --- | --- | --- |
| `python` | Alpine | Python, uv, pytest, Ruff, mypy |
| `nodejs` | Alpine | Node.js LTS, npm, Yarn, TypeScript, ESLint, Prettier |
| `devops` | Debian | AWS CLI, Azure CLI, Google Cloud CLI, Terraform, Ansible, kubectl, Helm |
| `go` | Alpine | Go, golangci-lint, Delve, Air |

The exact package and tool declarations are maintained in each stack's
`stack.yaml`. This table is the curated baseline, not a substitute for those
definitions.

## Base image selection

Each stack may select a supported base distribution (initially Alpine or
Debian) while reusing the same DevBox Core capabilities and behavior.

The DevOps stack uses Debian because some cloud vendor CLIs and their
dependencies do not provide equivalent official support on Alpine/musl.
Using Debian there improves compatibility with vendor-supported installation
methods and avoids fragile workarounds. Alpine remains the lighter choice for
the Python, Node.js and Go stacks.

Core installation must be distribution-aware: the same Core capabilities are
provided on both distributions, using the appropriate package manager and
package names. Stack-specific tools and packages must not leak into Core.

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

Stack definitions declare a channel or version policy, not a permanently
floating executable. During image build, the resolver/build tooling resolves
the channel to an exact version, records that version in generated build
metadata, and installs that exact version. The resulting image is immutable:
new upstream releases are picked up on the next image rebuild, not silently
inside an already-created container.

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

The current implementation supports schema version 1, which has pinned tool
versions and Alpine-only packages. The curated multi-base and release-channel
decisions above require a schema revision before implementation. The next
schema revision is expected to add:

| Field | Meaning |
| --- | --- |
| `base` | Supported distribution and version, initially Alpine or Debian. |
| `packages` | Distribution-specific additional packages. |
| `tools` | Supported tool identifiers and release channel policy (for example `lts` or `stable`). |
| `environment` | Environment variables available in the container. |

The schema remains strict: unknown fields are rejected, tool installers are
owned by DevBox, and stack files cannot execute arbitrary shell commands.

## Core and stack separation

The existing Core dependencies and integrations remain available in every
stack. This includes the DevBox CLI runtime, shell, Docker CLI integration,
Network Manager and host bridge behavior.

Terraform is removed from the current default image/Core installation and
belongs only to the DevOps stack. The DevBox bootstrap uv remains an internal
Core dependency; a user-facing uv installation belongs only to the Python
stack.

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
