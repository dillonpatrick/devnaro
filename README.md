# DevBox

A Docker-based development environment designed to keep development tools and dependencies out of the host system while providing a shared workspace for multiple projects.

DevBox combines Docker Compose, host-side Bash commands, a Python CLI, and an automatic Docker network manager.

## Features

- Containerized development tools based on Debian Trixie Slim.
- Persistent workspace stored outside the DevBox container.
- Host Docker integration through the mounted Docker socket.
- Open the current workspace path in the host VS Code with `code .` from inside DevBox.
- Automatic discovery and connection to eligible Docker Compose bridge networks.
- Persistent home directory across normal container stops and restarts.
- Separate stop and clean lifecycle operations.
- Host CLI for lifecycle operations and container-side CLI for diagnostics.
- Zsh, Oh My Zsh (pinned commit), Docker CLI, Python 3.13 from Debian Trixie packages, uv 0.13.7, Typer, and Rich.

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
|   |   +-- compose.sh (shared Docker Compose entry point)
|   |   +-- ui.sh (shared lifecycle terminal helpers)
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

### Host port publishing

DevBox does not publish development ports from its own container to the host by default. This avoids reserving broad port ranges and prevents unnecessary host-side listeners.

When a project needs to be reachable from the host browser, publish the required port in that project's own Docker Compose configuration, or use a project-specific forwarding solution. DevBox's `dm ports` feature serves a different purpose: it exposes a service from another Docker container on DevBox's own loopback interface so tools running inside DevBox can continue using `localhost`.


## Requirements

- Linux host.
- Docker Engine and Docker Compose plugin.
- Bash, Git, and GNU Make.
- Access to `/var/run/docker.sock`.
- VS Code CLI (`code`) on the host if you want to use `code .` from inside DevBox.

All DevBox build stages and runtime environments use Debian-based images. The host may use another Linux distribution if the requirements above are available. Python and Go are not required on the host: Python runs inside DevBox, and the small Go VS Code bridge is compiled during the Docker image build and extracted for host-side execution.

## Installation

Clone the repository and install the host command:

```bash
git clone git@github.com:dillonpatrick/devbox.git
cd devbox
make install
```

The installer requests sudo authentication before proceeding, but runs as your regular user so files in your home directory and repository keep the correct ownership. It creates a `devbox` symlink in `~/.local/bin` by default and adds that directory to PATH for Bash or Zsh. Set `DEVBOX_BIN_DIR` to install the command in a different directory; the installer adds that selected directory to PATH when it can identify a supported shell. Open a new terminal or source the shell configuration file printed by the installer. The installer is safe to run more than once.

Start the environment:

```bash
devbox start
```

The startup script detects host and Docker socket IDs, prepares the workspace, writes the local `.env`, and validates the Compose configuration. If the container is already running, it leaves it untouched; if it exists but is stopped, it starts that container without rebuilding; if it does not exist, it builds the image and creates the container. It then ensures the host VS Code bridge and Network Manager are running. It does not automatically enter the container.

### First-time setup: clone a project into the workspace

Starting DevBox only prepares the development environment. It does **not** clone your application repositories. Clone each project into the shared workspace from the **host terminal before entering the container**.

1. Start DevBox from the host:

   ```bash
   devbox start
   ```

2. Clone your project into the workspace from the host. **DevBox creates the workspace automatically** when you run `devbox start`. By default, it is a `workspace` directory alongside the DevBox repository:

   ```bash
   git clone <YOUR_PROJECT_GIT_URL> ../workspace/<PROJECT_NAME>
   ```

   Replace `<YOUR_PROJECT_GIT_URL>` with your repository URL and `<PROJECT_NAME>` with the directory name you want to use. If you configured a custom workspace with `devbox config set workspace PATH`, clone the project into that directory instead. There is no need to create the directory manually.

3. Enter the running container:

   ```bash
   devbox shell
   ```

4. Inside the container, go to the project directory. The host workspace is mounted at `/workspace`:

   ```bash
   cd /workspace/<PROJECT_NAME>
   ```

5. Start working. For example, to open the project in host VS Code:

   ```bash
   code .
   ```

The project files are stored on the host and shared with the container. You can also clone additional repositories into the workspace from the host at any time; they will appear under `/workspace` inside DevBox.

## Host commands

Run `devbox` commands in a host terminal. The canonical command list and descriptions are maintained in `scripts/host/command_registry.sh`; the CLI help, installer summary, and shell completion all read from that registry.

Use `devbox help` for the current command reference. Bash and Zsh completion are configured by `make install` and use the same registry, including nested `config` and `manager` commands.

Machine-specific settings are stored outside the repository in `~/.config/devbox/config` (or `$XDG_CONFIG_HOME/devbox/config`). An explicitly exported `WORKSPACE_PATH` takes precedence over the saved workspace setting.

### Lifecycle behavior

- **Stop:** runs `docker compose stop devbox`. The container remains stopped, and its image, Compose network, `devbox_home` volume, workspace, and host VS Code bridge are preserved. Use `devbox start` to bring it back.
- **Start:** leaves an already-running container untouched; starts an existing stopped container without rebuilding; builds the image and creates a container only when no container exists. It does not apply Dockerfile or Compose changes to an existing container. Use `devbox recreate` to recreate the container and network and apply those changes while preserving `devbox_home`.
- **Restart:** runs `docker compose restart devbox`. It only restarts the existing container; it does not recreate the container or network, rebuild the image, or change volumes.
- **Recreate:** removes and recreates the container and Compose network while preserving `devbox_home`; the host VS Code bridge is restarted.
- **Recreate all:** asks for confirmation, then removes the DevBox container, Compose network, `devbox_home` volume, local image, and host VS Code bridge before running the full startup flow. Workspace files and resources from other Compose projects are preserved. Files and settings stored in `devbox_home` are permanently lost.
- **Clean:** runs Compose cleanup for the DevBox project, removes its Compose-managed volumes and locally built images, and stops/removes the host VS Code bridge. It does not delete the workspace or resources belonging to other Compose projects.

Use `devbox clean` only when you intentionally want to remove DevBox's persisted home configuration and local image. A subsequent `devbox start` rebuilds what is needed.

- **Uninstall:** run `make uninstall` from the DevBox repository. It requests sudo authentication, then asks for confirmation before completely removing DevBox from the host. The script runs as your regular user to preserve file ownership. It removes the DevBox container, Compose network, `devbox_home` volume, locally built image, host VS Code bridge, command symlink, installer-managed PATH entries, machine-specific configuration, and generated local files. The DevBox repository and configured workspace are both preserved. If DevBox was installed to a custom directory with `DEVBOX_BIN_DIR`, pass the same variable to `make uninstall`.

## Inside the container

DevBox runs as root inside its isolated container. Install Debian packages directly with `apt-get update` and `apt-get install PACKAGE`; no sudo is needed. This does not make the process root on the host, but files created in the bind-mounted `/workspace` can be owned by root on the host. If that becomes inconvenient, adjust their ownership on the host. Manual package installations are not preserved when the container is recreated; add packages to the Dockerfile or selected stack definition for reproducible images. The container has access to the host Docker socket, so treat it as a trusted development environment.

After entering DevBox, the first interactive Zsh session after each container start/restart displays a welcome panel. The panel includes the current workspace, Network Manager status, and useful commands.

Every interactive Zsh prompt inside the container uses a compact two-line DevBox theme: a green `DEVBOX` identity, the current directory in cyan, the active Git branch, and a green prompt symbol. The host terminal prompt is not changed. The welcome panel and Python CLI use the same cyan/green visual language.

The `dm` command is a Zsh function available **inside the container only**. It is a shortcut for `devbox-manager`. Zsh tab completion for `devbox-manager` is enabled automatically; no manual installation command is needed.

### Open VS Code on the host

The `code` command inside DevBox forwards the current directory to the VS Code CLI installed on the Linux host and opens it through the **Dev Containers: Attach to Running Container** remote connection. The editor, integrated terminals, Python interpreter, debugger, and remote-capable extensions then run against the DevBox container instead of the host filesystem.

Install the **Dev Containers** extension (`ms-vscode-remote.remote-containers`) in host VS Code before using this command. DevBox checks for it and displays an actionable error if it is missing. The first connection installs the VS Code Server in the container; later connections reuse it.

From any project directory, run:

```bash
cd /workspace/project-1
code .
```

The host-side bridge is compiled as a static Go binary during the DevBox image build, then extracted to the host runtime directory by `devbox start`; no host Python or Go installation is needed. The bridge is removed by `devbox clean`. The host must have the VS Code `code` command available on its `PATH`. The bridge only opens paths inside the configured workspace.

The DevBox workspace opens with Zsh as its integrated terminal and uses the project's `.venv/bin/python` as the default Python interpreter when present. Install Python tooling extensions such as Python, Pylance, and Ruff in the **DevBox remote window** (the Extensions view distinguishes local and remote installations). Ruff is the configured Python formatter; this avoids requiring a separate Black Formatter process.

## Makefile tasks

Run these tasks from the DevBox repository directory on the host. They are for development and maintenance; use the `devbox` command for everyday operations.

| Command | Description |
|---|---|
| `make` | Show available tasks |
| `make install` | Authenticate with sudo and install the host-side `devbox` command |
| `make uninstall` | Authenticate with sudo and completely remove DevBox while preserving the repository and workspace |
| `make build` | Build the DevBox image |
| `make rebuild` | Rebuild the image without cache |
| `make test` | Run Python unit tests (DevBox must be running) |
| `devbox ci` | Run the GitHub Actions workflow locally using act |
| `make config` | Validate Docker Compose configuration |
| `make clean` | Remove DevBox containers, networks, volumes, and local images |

## Python CLI

The project requires Python 3.12 or newer. The `devbox-manager` Python CLI is installed inside the container in an isolated virtual environment at `/opt/devbox-venv`. The `dm` shortcut invokes the same CLI.

Available commands include `info` (container environment and host integrations), status, health checks, network listing, port forwarding, and Network Manager status/logs. Use `dm --help` or `devbox-manager --help` inside the container for the current command reference.

## Local service port forwarding

DevBox can expose a project service on its own loopback interface without changing the project's connection string. The Port Forwarding Manager reads persistent mappings from `~/.config/devbox/port-forwards.json` and starts a TCP listener bound only to `127.0.0.1` inside DevBox. It forwards traffic to the target service or container name on a Docker network connected to DevBox.

Configure a mapping from inside the container:

```bash
dm ports add 5432 warranty-manager-db 5432
dm ports list
```

The example makes PostgreSQL available to processes running inside DevBox at `localhost:5432`. Use the Compose service name (for example, `db`) or a container name as the target. The target must be reachable on a Docker network connected to DevBox.

Remove a mapping with:

```bash
dm ports remove 5432
```

Local ports must be unique. The listener binds to DevBox loopback, not to the host or external network interfaces. The mapping survives container recreation because it is stored in the persistent DevBox home volume. The manager starts automatically with the container and retries a stopped forwarding process.

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

## Local GitHub Actions

Run the repository validation workflow on the host with `devbox ci`. The command installs a pinned, checksum-verified `act` binary into `~/.local/bin` on first use, then runs the workflow against the host Docker Engine. Docker must be running. Use `devbox ci --list` to list jobs or `devbox ci -j python-tests` to run one job. The workflow runs in containers, so the first execution downloads the runner image. Local execution is a close approximation, not a guarantee of identical behavior to GitHub-hosted runners.

## Development

The Python CLI source is in `src/devbox_manager/`. Dependencies and the console entry point are declared in `pyproject.toml`. Unit tests are in `tests/unit/`.

