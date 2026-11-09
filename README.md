# DevBox

A Docker-based development environment designed to keep development tools and dependencies out of the host system while providing a shared workspace for multiple projects.

DevBox combines Docker Compose, host-side Bash commands, a Python CLI, and an automatic Docker network manager.

## Features

- Containerized development tools based on Ubuntu 24.04.
- Persistent workspace stored outside the DevBox container.
- Host Docker integration through the mounted Docker socket.
- Open the current workspace path in the host VS Code with `code .` from inside DevBox.
- Automatic discovery and connection to eligible Docker Compose bridge networks.
- Persistent home directory across normal container stops and restarts.
- Separate stop and clean lifecycle operations.
- Host CLI for lifecycle operations and container-side CLI for diagnostics.
- Zsh, Oh My Zsh (pinned commit), Terraform 1.17.1, Docker CLI, Python 3.12+, uv 0.13.7, Typer, and Rich.

## Architecture

```text
Host
|
+-- devbox/
|   +-- .devcontainer/
|   +-- .github/
|   +-- docker/
|   |   +-- Dockerfile
|   |   +-- docker-compose.yml
|   +-- network_manager/
|   |   +-- manager.py
|   +-- scripts/
|   |   +-- host/
|   |   |   +-- devbox
|   |   |   +-- install.sh
|   |   |   +-- start.sh
|   |   |   +-- stop.sh
|   |   |   +-- clean.sh
|   |   +-- container/
|   |       +-- entrypoint.sh
|   +-- src/devbox_manager/
|   +-- tests/unit/
|   +-- Makefile
|   +-- pyproject.toml
|   +-- README.md
|
+-- workspace/
    +-- project-1/
    +-- project-2/
```

The workspace is mounted in the container at `/workspace`. Project Compose files remain in their own directories and do not need to be changed by DevBox.

### Development port forwarding

DevBox publishes common development ports from the container to the host, bound **only to `127.0.0.1`**. This lets the host browser open links printed by tools such as Uvicorn, Vite, and other local development servers without changing a project's Compose file.

Published host/container ports are `3000–3010`, `4173`, `5000–5010`, `5173`, `8000–8010`, `8080–8090`, and `9000–9010`. The host and container use the same port number. For example, an API listening on container port `8000` is reachable on the host at `http://127.0.0.1:8000`.

Applications started directly inside DevBox must bind to `0.0.0.0`, not `127.0.0.1`, so Docker can forward traffic to them. For example:

```bash
uv run uvicorn warranty_manager.main:app --reload --host 0.0.0.0 --port 8000
```

The host-side bindings are loopback-only and are not exposed to other machines on the network. If a published host port is already occupied, Docker may refuse to start DevBox; stop the conflicting host service or adjust the published port list in `docker/docker-compose.yml`.

## Requirements

- Linux host.
- Docker Engine and Docker Compose plugin.
- Bash, Git, and GNU Make.
- Access to `/var/run/docker.sock`.

The container image is based on Ubuntu 24.04. The host may use another Linux distribution if the requirements above are available. Python 3 is also required on the host for the VS Code path bridge.

## Installation

Clone the repository and install the host command:

```bash
git clone git@github.com:dillonpatrick/devbox.git
cd devbox
make install
```

The installer creates a `devbox` symlink in `~/.local/bin` by default and adds that directory to PATH for Bash or Zsh. Set `DEVBOX_BIN_DIR` to install the command in a different directory; the installer adds that selected directory to PATH when it can identify a supported shell. Open a new terminal or source the shell configuration file printed by the installer. The installer is safe to run more than once.

Start the environment:

```bash
devbox start
```

The startup script detects host and Docker socket IDs, prepares the workspace, writes the local `.env`, validates the Compose configuration, builds and starts the container, and starts the Network Manager. It does not automatically enter the container.

## Host commands

Run these commands in a host terminal:

| Command | Description |
|---|---|
| `devbox` or `devbox shell` | Enter the running DevBox container |
| `devbox start` | Build (if needed) and start DevBox |
| `devbox stop` | Stop the container without removing resources |
| `devbox clean` | Remove DevBox containers, networks, volumes, and local images |
| `devbox restart` | Recreate DevBox while preserving its home volume |
| `devbox status` | Show container status |
| `devbox logs` | Show container logs |
| `devbox networks` | Show networks connected to DevBox |
| `devbox doctor` | Run container-side health checks |
| `devbox manager status` | Show Network Manager process status |
| `devbox manager logs` | Show Network Manager logs |
| `devbox config` | Show machine-specific configuration |
| `devbox config set workspace PATH` | Set the workspace directory |
| `devbox help` | Show this help message |

Machine-specific settings are stored outside the repository in `~/.config/devbox/config` (or `$XDG_CONFIG_HOME/devbox/config`). An explicitly exported `WORKSPACE_PATH` takes precedence over the saved workspace setting.

### Lifecycle behavior

- **Stop:** runs `docker compose stop devbox`. The container remains stopped, and its image, Compose network, `devbox_home` volume, workspace, and host VS Code bridge are preserved. Use `devbox start` to bring it back.
- **Start:** runs the normal startup flow. Docker Compose reuses the existing stopped container and persistent volume when possible.
- **Restart:** recreates the container and Compose network while preserving `devbox_home`; the host VS Code bridge is restarted.
- **Clean:** runs Compose cleanup for the DevBox project, removes its Compose-managed volumes and locally built images, and stops/removes the host VS Code bridge. It does not delete the workspace or resources belonging to other Compose projects.

Use `devbox clean` only when you intentionally want to remove DevBox's persisted home configuration and local image. A subsequent `devbox start` rebuilds what is needed.

## Inside the container

After entering DevBox, the first interactive Zsh session after each container start/restart displays a welcome panel. The panel includes the current workspace, Network Manager status, and useful commands.\n\nEvery interactive Zsh prompt inside the container uses a compact two-line layout: a green `[DEVBOX]` marker, the current directory, the Git branch, and a separate command line. The host terminal prompt is not changed.

The `dm` command is a Zsh function available **inside the container only**. It is a shortcut for `devbox-manager`.

### Open VS Code on the host

The `code` command inside DevBox forwards the current directory to the VS Code CLI installed on the Linux host. It opens the project as a temporary VS Code workspace (stored under the host cache, not inside the project) and configures **DevBox** as that workspace's default integrated terminal profile. Open the terminal with <kbd>Ctrl</kbd>+<kbd>`</kbd> or **Terminal → New Terminal**; it starts a Zsh session inside the running DevBox container at the matching `/workspace/...` directory. Additional terminals in that workspace use the same profile.

If DevBox is stopped, the terminal displays an instruction to run `devbox start` from a host terminal; it does not start or recreate the container automatically. The host must have Docker Compose access and the VS Code `code` command available.

From any project directory, run:

```bash
cd /workspace/project-1
code .
```

The host-side bridge is started by `devbox start` and removed by `devbox clean`. The host must have the VS Code `code` command available on its `PATH`. The bridge only opens paths inside the configured workspace.

| Command | Description |
|---|---|
| `dm status` | Show DevBox container status |
| `dm doctor` | Run environment health checks |
| `dm networks` | List networks connected to DevBox |
| `dm network-manager status` | Check Network Manager process |
| `dm network-manager logs` | Show recent log lines |
| `docker ps` | List running containers |
| `docker compose up -d` | Start services in the current project directory |

Run project-specific Docker Compose commands from that project's directory, for example:

```bash
cd /workspace/project-1
docker compose up -d
```

## Makefile tasks

Run these tasks from the DevBox repository directory on the host. They are for development and maintenance; use the `devbox` command for everyday operations.

| Command | Description |
|---|---|
| `make` | Show available tasks |
| `make install` | Install the host-side `devbox` command |
| `make build` | Build the DevBox image |
| `make rebuild` | Rebuild the image without cache |
| `make test` | Run Python unit tests (DevBox must be running) |
| `make config` | Validate Docker Compose configuration |
| `make clean` | Remove DevBox containers, networks, volumes, and local images |

## Python CLI

The project requires Python 3.12 or newer. The `devbox-manager` Python CLI is installed inside the container in an isolated virtual environment at `/opt/devbox-venv`. The `dm` shortcut invokes the same CLI.

Available command groups include status, health checks, network listing, and Network Manager status/logs. Use `dm --help` or `devbox-manager --help` inside the container for the current command reference.

## Network Manager

The Network Manager runs inside DevBox and reconciles Docker networks every 10 seconds by default.

By default, it considers networks that:

- Use the `bridge` driver.
- Have the Docker Compose project label.
- Are not marked as internal.
- Have IPAM configuration.
- Are not named in the exclusion list (default: `bridge,host,none`).

It persists the network IDs it manages in:

```text
~/.local/state/devbox-network-manager/managed-networks.json
```

The manager only disconnects networks it previously recorded as managed. This state is stored in the `devbox_home` volume.

View logs from the host with `devbox manager logs`, or from inside the container with `dm network-manager logs`.

## Configuration

The startup script generates a local `.env` file, which is ignored by Git.

| Variable | Description |
|---|---|
| `USERNAME` | DevBox user |
| `USER_UID` | Host user ID |
| `USER_GID` | Host group ID |
| `DOCKER_GID` | Docker socket group ID |
| `TZ` | Host timezone |
| `WORKSPACE_PATH` | Absolute workspace path |

The following build arguments can be set in the local `.env` file to update pinned tools deliberately:

| Variable | Default | Description |
|---|---|---|
| `TERRAFORM_VERSION` | `1.17.1` | Terraform version installed in the image |
| `UV_VERSION` | `0.13.7` | uv version installed in the image |
| `OH_MY_ZSH_COMMIT` | `cca3bdfbef8c52ef8939ce7911ff68852b949daa` | Exact Oh My Zsh commit |

The Network Manager also supports:

| Variable | Default | Description |
|---|---|---|
| `NETWORK_SYNC_INTERVAL` | `10` | Synchronization interval in seconds |
| `NETWORK_EXCLUDE` | `bridge,host,none` | Comma-separated excluded network names |
| `NETWORK_COMPOSE_ONLY` | `true` | Only manage Compose networks |
| `NETWORK_EXCLUDE_INTERNAL` | `true` | Ignore internal networks |
| `NETWORK_MANAGER_STATE_DIR` | User state directory | Persistent manager state location |

## Security

The mounted Docker socket grants extensive control over the host Docker Engine. Treat DevBox as a privileged development environment and only run trusted project code.

## Development

The Python CLI source is in `src/devbox_manager/`. Dependencies and the console entry point are declared in `pyproject.toml`. Unit tests are in `tests/unit/`.
