# DevBox

A containerized development environment powered by Docker, designed to keep the host machine clean while providing a consistent workspace for multiple projects.

DevBox combines Docker Compose, Bash bootstrap scripts, and a Python CLI with Rich-powered terminal output.

## Features

- **Isolated environment:** Keep development tools and dependencies inside a Docker container.
- **Persistent workspace:** Store projects outside the DevBox container lifecycle.
- **Docker integration:** Manage host Docker resources through the mounted Docker socket.
- **Automatic network discovery:** Connect DevBox to eligible Docker Compose bridge networks.
- **Persistent home directory:** Preserve user configuration between container restarts.
- **Python CLI:** Inspect container status, networks, health checks, and Network Manager logs.
- **Developer experience:** Zsh, Oh My Zsh, Terraform, Docker CLI, Python, uv, Typer, and Rich.

## Architecture

```text
Host Machine
|
+-- devbox/
|   +-- .devcontainer/
|   |   +-- devcontainer.json
|   +-- devbox_manager/
|   |   +-- cli.py
|   |   +-- config.py
|   |   +-- docker_client.py
|   |   +-- network_manager.py
|   +-- network-manager/
|   |   +-- manager.py
|   +-- scripts/
|   +-- Dockerfile
|   +-- docker-compose.yml
|   +-- pyproject.toml
|   +-- Makefile
|   +-- start.sh
|   +-- stop.sh
|
+-- workspace/
    +-- project-1/
    +-- project-2/
    +-- project-3/
```

The workspace is mounted into the container at `/workspace`. The Network Manager discovers eligible Compose networks and connects the DevBox container automatically.

### Responsibilities

| Component | Responsibility |
|---|---|
| Bash scripts | Host bootstrap and teardown |
| Docker Compose | Container, volume, and socket configuration |
| Python CLI | Operational commands and diagnostics |
| Network Manager | Periodic Docker network reconciliation |
| Makefile | Convenient command shortcuts |

## Requirements

- Linux host.
- Docker Engine.
- Docker Compose plugin.
- Bash.
- Git.
- GNU Make.
- Access to `/var/run/docker.sock`.

The current container image is based on Ubuntu 22.04. The host can use another Linux distribution as long as the requirements above are available.

## Installation

### 1. Clone the repository

```bash
git clone git@github.com:dillonpatrick/devbox.git
cd devbox
```

### 2. Start DevBox

```bash
chmod +x start.sh stop.sh
make start
```

The startup script:

1. Detects host UID and GID.
2. Detects the Docker socket group ID.
3. Creates or reuses the sibling `workspace` directory.
4. Generates the local `.env` file.
5. Validates Docker Compose.
6. Builds and starts the DevBox container.
7. Starts the Network Manager.
8. Adds a `devbox` shell alias when the host shell is supported.
9. Opens an interactive Zsh session.

The Python CLI and its dependencies are installed into an isolated virtual environment in the container image. No Python packages are installed on the host.

## Using DevBox

### Enter the environment

From the host, after loading the configured shell file (for example, `source ~/.bashrc` or `source ~/.zshrc`), use:

```bash
devbox
```

Alternatively:

```bash
make shell
```

### Work with projects

Inside DevBox:

```bash
cd /workspace
cd project-1
docker compose up -d
```

The Network Manager discovers eligible project networks. Project Compose files do not need to be modified.

## Python CLI

The `devbox-manager` command runs inside the DevBox container.

| Command | Description |
|---|---|
| `devbox-manager --help` | Show CLI help |
| `devbox-manager --version` | Show CLI version |
| `devbox-manager status` | Show detailed container status |
| `devbox-manager doctor` | Run basic environment health checks |
| `devbox-manager networks` | List networks attached to DevBox |
| `devbox-manager network-manager status` | Check Network Manager process |
| `devbox-manager network-manager logs` | Show recent Network Manager logs |
| `devbox-manager network-manager logs -n 100` | Show the last 100 log lines |

The CLI uses Typer for command handling and Rich for formatted terminal output.

### Makefile shortcuts

Run these commands from the repository directory on the host:

| Command | Description |
|---|---|
| `make` | Show available commands |
| `make start` | Start DevBox |
| `make stop` | Stop and remove DevBox resources |
| `make restart` | Restart DevBox |
| `make build` | Build the image |
| `make rebuild` | Rebuild without cache |
| `make status` | Show Compose container status |
| `make doctor` | Run Python health checks |
| `make cli-status` | Show detailed DevBox status |
| `make cli-networks` | Show attached networks |
| `make manager-status` | Check Network Manager |
| `make manager-logs` | Show Network Manager logs |
| `make logs-follow` | Follow container logs |
| `make config` | Validate Compose configuration |
| `make clean` | Remove DevBox containers, network, and home volume |

## Network Manager

The Network Manager runs inside the DevBox container and periodically reconciles Docker networks.

By default, it considers networks that:

- Use the `bridge` driver.
- Have the Docker Compose project label.
- Are not marked as internal.
- Have IPAM configuration.
- Are not explicitly excluded.

The default synchronization interval is 10 seconds.

The manager persists the network IDs it connected in:

```text
/home/devuser/.local/state/devbox-network-manager/managed-networks.json
```

It only disconnects networks recorded as managed by the process. The state is stored in the persistent home volume.

Network Manager logs are available through:

```bash
make manager-logs
```

## Configuration

The startup script generates a local `.env` file. It is intentionally ignored by Git.

| Variable | Description |
|---|---|
| `USERNAME` | DevBox user |
| `USER_UID` | Host user ID |
| `USER_GID` | Host group ID |
| `DOCKER_GID` | Docker socket group ID |
| `TZ` | Host timezone |
| `WORKSPACE_PATH` | Absolute workspace path |

The Network Manager also supports:

| Variable | Default | Description |
|---|---|---|
| `NETWORK_SYNC_INTERVAL` | `10` | Synchronization interval in seconds |
| `NETWORK_EXCLUDE` | `bridge,host,none` | Comma-separated excluded network names |
| `NETWORK_COMPOSE_ONLY` | `true` | Only manage Compose networks |
| `NETWORK_EXCLUDE_INTERNAL` | `true` | Ignore internal networks |
| `NETWORK_MANAGER_STATE_DIR` | User state directory | Persistent manager state location |

## Stopping and cleanup

Stop DevBox:

```bash
make stop
```

This removes the DevBox container, its Compose network, and the persistent `devbox_home` volume. The workspace, project containers, project volumes, and images are preserved.

**Warning:** removing `devbox_home` also removes the persisted shell configuration and Network Manager state.

## Security note

The Docker socket grants extensive control over the host Docker Engine. Treat the DevBox container as a privileged development environment and only run trusted project code.

## Development

The Python CLI source is in `devbox_manager/`. Dependencies and the console entry point are declared in `pyproject.toml`.

The container image installs the CLI into `/opt/devbox-venv`, keeping its Python dependencies isolated from Ubuntu's system Python packages.
