# DevBox Alpine experiment

This is an isolated, side-by-side experiment. It does not replace the Ubuntu
image or change the default `docker/docker-compose.yml`.

## Isolation guarantees

- Separate Compose project name: `devbox-alpine`.
- Separate container: `devbox-alpine`.
- Separate persistent home volume: `devbox_alpine_home`.
- No host port publishing, so the Ubuntu DevBox port bindings cannot conflict.
- The workspace is intentionally shared at the configured `WORKSPACE_PATH`.
- The Docker socket is mounted to exercise Docker CLI and Network Manager
  integration. As with the regular DevBox, this grants extensive control over
  the host Docker Engine.

Do not run `docker compose down --volumes` without the Alpine file and project
name: always use the commands below so cleanup is scoped to this experiment.

## Build and start

Run from the repository root on the host:

```bash
export WORKSPACE_PATH="$HOME/Work/workspace"
export USER_UID="$(id -u)"
export USER_GID="$(id -g)"
export DOCKER_GID="$(stat -c '%g' /var/run/docker.sock)"

docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml config --quiet

docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml build

docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml up -d

docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml exec devbox-alpine zsh
```

If your workspace is not `$HOME/Work/workspace`, set `WORKSPACE_PATH` to
the same absolute workspace directory used by your regular DevBox.

## Smoke tests inside Alpine

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

Check Docker socket access and inspect whether the Network Manager can discover
and connect to eligible Compose networks:

```bash
docker ps
python /opt/network-manager/manager.py
```

The last command runs in the foreground; stop it with Ctrl+C after checking
its output. For persistent testing, start it detached as in the regular
environment.

## Stop and remove only the experiment

Stop while preserving its container and home volume:

```bash
docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml stop
```

Remove the Alpine container, its Compose network, and its dedicated home
volume (this intentionally resets Alpine's persisted shell configuration):

```bash
docker compose --project-directory . -p devbox-alpine \
  -f docker/docker-compose.alpine.yml down --volumes
```

The Ubuntu DevBox uses another Compose project, container, and volume. These
commands do not target or remove them.

## Comparison checklist

Record results for both images under comparable conditions:

1. Image size (`docker image ls`).
2. Clean build duration.
3. Container startup duration.
4. Python 3.12, uv lockfile installation, and unit-test compatibility.
5. Terraform, Docker CLI, and Docker Compose functionality.
6. Zsh, Oh My Zsh, autosuggestions, syntax highlighting, and prompt.
7. Docker socket permissions and Network Manager behavior.
8. Workspace permissions and VS Code host integration.

The VS Code bridge is host-side in the regular startup flow. This isolated
Compose setup does not start a separate host bridge; the Alpine `code`
command therefore is not expected to work until a dedicated bridge socket is
configured and mounted. This is kept out of the first experiment to avoid
interfering with the active Ubuntu bridge.

Alpine uses musl rather than glibc. A successful image build is not sufficient:
run the smoke tests and project workloads before considering adoption.
