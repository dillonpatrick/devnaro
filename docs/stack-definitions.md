# Stack Definition Contract

## Purpose

A stack describes the development tools and environment-specific configuration
that DevBox should include in an image. It does not define Docker build steps,
container orchestration, arbitrary shell commands or host integration.

The contract is intentionally small and versioned. DevBox resolves and
validates the YAML before the runtime image is built.

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

All top-level fields are required. Unknown fields are rejected.

### Tool declarations

Tools are declared by identifier and version. DevBox owns the installer for
each supported tool. A stack cannot provide an installer command or arbitrary
build instructions.

The supported tool identifiers are:

- `terraform`
- `uv`

A tool is installed only when it is declared in the selected stack. New tool
identifiers require an implementation and tests in DevBox before they can be
referenced by a stack.

The DevBox CLI has its own Python runtime and bootstrap uv installation.
These are Core implementation dependencies, not stack-provided development
tools. The stack's `uv`, when declared, is installed separately for user
workloads.

### Package declarations

Only additional packages belong in `packages.alpine`. Packages that are part
of the DevBox Core runtime must not be repeated in a stack definition.

Package names use the same validation rules as the existing package manifest.
Unavailable optional packages retain the warning-and-skip behavior;
repository/network failures remain fatal.

Stack packages are combined with the user-managed entries in
`docker/packages.txt` during image build. Duplicate package names are
installed only once.

### Environment declarations

Environment values must be strings, and variable names must use uppercase
letters, digits and underscores, beginning with a letter or underscore.

Values are written to a shell-safe environment file and loaded for Zsh login
sessions in the container. The initial contract does not support secret
values, variable interpolation, shell expansion or host-specific paths.

## Resolution and image build

The Docker build uses a dedicated temporary `stack-resolver` stage based on
Python 3.12 Alpine. It installs PyYAML in that stage, loads the selected
`stacks/<name>/stack.yaml`, validates it and writes normalized build inputs.

The runtime image consumes those generated files to install the selected
Alpine packages and supported tools and to configure the stack environment.
The resolver stage and its PyYAML dependency are not copied into the final
image. The host does not need Python or PyYAML to resolve a stack.

The selected stack is passed to the build through the `STACK_NAME` build
argument, which defaults to `default`. Changing stack tools or packages
requires rebuilding the image; this is intentional for reproducibility.

Generated build inputs include:

- `alpine-packages.txt`
- `terraform-version`
- `uv-version`
- `environment.sh`
- `stack-name`

## Default stack

`stacks/default/stack.yaml` preserves the existing default development
toolset. It currently declares Terraform and uv versions and no additional
Alpine packages or environment variables.

## Explicit non-goals for schema version 1

- Arbitrary shell commands or custom installer scripts.
- Stack inheritance or composition.
- Docker services, ports, volumes or networks.
- Secrets and host-specific configuration.
- Runtime package installation.
- Per-environment package manifests or multi-instance orchestration.
