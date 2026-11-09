# DevBox Alpine experiment

This branch provides two isolated Alpine variants for comparison. Neither
changes the default Ubuntu image or `docker/docker-compose.yml`.

## Variants

| Variant | Base image | Purpose |
|---|---|---|
| Alpine with Python | `python:3.12-alpine3.22` | Convenience baseline with Python preinstalled |
| Minimal Alpine | `alpine:3.22` | Measure the cost of installing Python and the toolchain ourselves |

Both variants use distinct Compose projects, containers, and named home volumes.
They share only the configured workspace and the host Docker socket. Neither
publishes host ports, so they can coexist with the Ubuntu DevBox without port
collisions.

The minimal variant installs Python 3.12 from Alpine's `apk` repository and
fails the build if the package version is not Python 3.12. It then installs
`uv` in a dedicated virtual environment and syncs the same locked DevBox CLI
dependencies as the other variants.

## Configure host values

Run commands below from the repository root on the host. Set the workspace to
the same absolute path used by your regular DevBox:

```bash
export WORKSPACE_PATH="$HOME/Work/workspace"
export USER_UID="$(id -u)"
export USER_GID="$(id -g)"
export DOCKER_GID="$(stat -c '%g' /var/run/docker.sock)"
```

Adjust `WORKSPACE_PATH` if your workspace lives elsewhere.

## Variant A: Alpine with Python preinstalled

Validate, build, and start:

```bash
docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml config --quiet

docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml build

docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml up -d
```

Enter the container:

```bash
docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml exec devbox-alpine zsh
```

## Variant B: Minimal Alpine base

Validate, build, and start:

```bash
docker compose --project-directory . -p devbox-alpine-minimal \
  -f docker/docker-compose.alpine-minimal.yml config --quiet

docker compose --project-directory . -p devbox-alpine-minimal \
  -f docker/docker-compose.alpine-minimal.yml build

docker compose --project-directory . -p devbox-alpine-minimal \
  -f docker/docker-compose.alpine-minimal.yml up -d
```

Enter the container:

```bash
docker compose --project-directory . -p devbox-alpine-minimal \
  -f docker/docker-compose.alpine-minimal.yml exec devbox-alpine-minimal zsh
```

## Smoke tests inside either container

Run these checks inside each container:

```bash
cat /etc/alpine-release
python --version
uv --version
terraform version
docker version
docker compose version
zsh --version
devbox-manager --help
dm --help
```

Check Docker socket access:

```bash
docker ps
```

The Network Manager currently identifies the DevBox container using its
container hostname. The Alpine variants have distinct container names, so the
manager may report that the `devbox` container was not found. This is a known
integration gap to evaluate/fix separately; it does not by itself mean the
Alpine container failed to start.

## Stop and remove only one variant

Stop a variant while preserving its container and home volume:

```bash
# Python-preinstalled Alpine
docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml stop

# Minimal Alpine
docker compose --project-directory . -p devbox-alpine-minimal \
  -f docker/docker-compose.alpine-minimal.yml stop
```

Remove one variant and its dedicated home volume (this resets that variant's
persisted shell configuration):

```bash
# Python-preinstalled Alpine
docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml down --volumes

# Minimal Alpine
docker compose --project-directory . -p devbox-alpine-minimal \
  -f docker/docker-compose.alpine-minimal.yml down --volumes
```

These commands are explicitly scoped to the selected experiment. They do not
target the Ubuntu DevBox or the other Alpine variant.

## Comparison checklist

Record results for all three images under comparable conditions:

1. Final image size (`docker image ls`).
2. Clean build duration.
3. Container startup duration.
4. Python 3.12 and uv lockfile installation.
5. Terraform, Docker CLI, and Docker Compose functionality.
6. Zsh, Oh My Zsh, autosuggestions, syntax highlighting, and prompt.
7. Docker socket permissions.
8. Workspace permissions and representative project workloads.

Alpine uses musl rather than glibc. A successful image build is not sufficient:
run the smoke tests and real project workloads before considering adoption.
The VS Code host bridge is not started by either isolated Compose setup; the
container-side `code` command is not expected to work until a dedicated bridge
socket is configured and mounted.
