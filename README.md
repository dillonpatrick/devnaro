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
|   |   +-- devbox
|   +-- Dockerfile
|   +-- docker-compose.yml
|   +-- pyproject.toml
|   +-- Makefile
|   +-- install.sh
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
| `install.sh` | Installs the host-side `devbox` command |\n| `start.sh` / `stop.sh` | DevBox startup and teardown |
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

### 2. Configure the host

```bash
chmod +x install.sh start.sh stop.sh
make install
```

The installer creates or updates `~/.local/bin/devbox` as a symlink to the repository's host CLI and adds `~/.local/bin` to the supported shell's PATH configuration. It is safe to run more than once. Open a new terminal, or source the shell configuration file printed by the installer. The installer also removes the legacy DevBox alias block from previous versions.

### 3. Start DevBox

```bash
make start
```

The startup script detects host and Docker socket IDs, creates or reuses the sibling `workspace` directory, generates the local `.env`, validates Compose, builds and starts the container, and starts the Network Manager. It does not configure the host shell or automatically enter the container.

## Using DevBox

### Enter the environment

From the host, after installing the CLI and loading the updated PATH, use:

```bash
devbox                 # Enter DevBox (default)
devbox start           # Build and start DevBox
devbox status          # Show container status
devbox shell           # Enter DevBox
devbox doctor           # Run health checks
devbox networks        # Show attached networks
devbox manager logs    # Show Network Manager logs
devbox stop            # Stop and remove DevBox resources
devbox help            # Show all commands
```

The `devbox restart` command recreates the container without deleting the persistent `devbox_home` volume. Use `devbox stop` when you intentionally want to remove DevBox resources, including that volume.

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
| `make install` | Install the host-side `devbox` command |\n| `make start` | Start DevBox without entering it |
| `make stop` | Stop and remove DevBox resources |
| `make restart` | Restart DevBox |
| `make build` | Build the image |
| `make rebuild` | Rebuild without cache |
| `make status` | Show Compose container status |
| `make doctor` | Run Python health checks |
| `make test` | Run Python unit and smoke tests |
| `make cli-status` | Show detailed DevBox status |
| `make cli-networks` | Show attached networks |
| `make manager-status` | Check Network Manager |
| `make manager-logs` | Show Network Manager logs |
| `make logs-follow` | Follow container logs |
| `make config` | Validate Compose configuration |
| `make clean` | Remove DevBox containers, network, and home volume |

## Testing

The test suite uses pytest and runs inside the DevBox container:

```bash
make test
```

Tests cover CLI help/version output and Network Manager process/log diagnostics. No external Docker daemon is required for these unit and smoke tests.

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
