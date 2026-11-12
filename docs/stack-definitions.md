# Stack Definition Contract

## Purpose

A stack describes the development tools and environment-specific configuration
that DevBox should include in an image. It does not define Docker build steps,
container orchestration, arbitrary shell commands, or host integration.

The initial contract is intentionally small and versioned.

## File location

Each stack is stored at:

```text
stacks/<stack-name>/stack.yaml
```

The directory name and the `name` field must match.

## Schema version 1

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `schema_version` | integer | yes | Definition format version; currently `1`. |
| `name` | string | yes | Stable stack identifier. |
| `description` | string | yes | Human-readable summary. |
| `packages.alpine` | list of strings | yes | Additional Alpine packages installed with `apk`. |
| `tools` | mapping | yes | Supported tool identifiers and pinned versions. |
| `environment` | mapping of strings to strings | yes | Environment variables available in the container. |

### Tool declarations

Tools are declared by identifier and version. The DevBox implementation owns
the installer for each supported tool. A stack cannot provide an installer
command or arbitrary build instructions.

The initial supported tool identifiers are:

- `terraform`
- `uv`

New tool identifiers require an implementation and tests in DevBox before
they can be referenced by a stack.

### Package declarations

Only additional packages belong in `packages.alpine`. Packages that are part
of the DevBox Core runtime must not be repeated in a stack definition.

Package names must follow the existing package-manifest validation contract.
Unavailable optional packages retain the current warning-and-skip behavior;
repository/network failures remain fatal.

### Environment declarations

Environment values must be strings. The initial contract does not support
secret values, variable interpolation, shell expansion, or host-specific
paths. Those concerns belong to later, explicitly designed features.

## Default stack

`stacks/default/stack.yaml` is the migration baseline. Its purpose is to
preserve the currently available Terraform and uv versions while the image
build is decoupled.

The Docker build runs the Python Stack Resolver in a dedicated temporary
stage. The resolver validates the selected stack and emits normalized package,
tool-version and environment artifacts consumed by the runtime image stage.
The final image does not include the resolver stage or its PyYAML dependency.

## Explicit non-goals for schema version 1

- Arbitrary shell commands or custom installer scripts.
- Stack inheritance or composition.
- Docker services, ports, volumes, or networks.
- Secrets and host-specific configuration.
- Runtime package installation.
