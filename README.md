# DevBox

A containerized development environment powered by Docker, designed to keep your host machine clean while providing a flexible and isolated workspace for multiple projects.

DevBox provides a consistent development environment with essential engineering tools, Docker integration, and automatic network discovery between containers.

## Features

- **Isolated environment:** Keep development tools and dependencies inside a Docker container.
- **Persistent workspace:** Store projects outside the DevBox container lifecycle.
- **Docker integration:** Manage host Docker containers directly from the DevBox.
- **Automatic network discovery:** Connect the DevBox to eligible Docker Compose networks automatically.
- **Persistent home directory:** Preserve user configuration between restarts.
- **Infrastructure tools:** Preinstalled Terraform, Docker CLI, Docker Compose, Python, and `uv`.
- **Developer experience:** Zsh with Oh My Zsh and useful plugins.

## Architecture

```text
Host Machine
│
├── devbox/
│   ├── Dockerfile
│   ├── compose.yaml
│   ├── start.sh
│   ├── stop.sh
│   └── network-manager/
│       └── manager.py
│
├── workspace/
│   ├── project-1/
│   ├── project-2/
│   └── project-3/
│
└── Docker Engine
    │
    ├── DevBox
    │   ├── Docker CLI
    │   ├── Python
    │   ├── Terraform
    │   └── Network Manager
    │
    ├── Project containers
    │   └── Docker Compose networks
    │
    └── Persistent project volumes
```

The workspace is mounted into the DevBox container at `/workspace`.

The Network Manager periodically discovers eligible Docker Compose bridge networks and connects the DevBox automatically.

## Requirements

Before getting started, make sure you have:

- Linux host with Docker Engine installed.
- Docker Compose plugin.
- Bash.
- Git.
- Access to `/var/run/docker.sock`.

The current configuration is designed for Ubuntu-based Docker environments.

## Installation

### 1. Clone the repository

```bash
git clone git@github.com:dillonpatrick/devbox.git
cd devbox
```

### 2. Review configuration

The default configuration uses:

| Setting | Default value |
|---|---|
| Username | `devuser` |
| Workspace | `../workspace` |
| Base image | Ubuntu 22.04 |
| Timezone | Host timezone |
| Persistent home | `devbox_home` |
| Network Manager interval | 10 seconds |

The workspace is created at the same directory level as the DevBox repository.

### 3. Start DevBox

Make the startup script executable:

```bash
chmod +x start.sh
```

Start the environment:

```bash
./start.sh
```

The startup script automatically:

1. Detects host UID and GID.
2. Detects the Docker socket group ID.
3. Creates or reuses the workspace directory.
4. Generates the `.env` configuration file.
5. Validates the Docker Compose configuration.
6. Builds the DevBox image.
7. Starts the DevBox container.
8. Starts the Network Manager.
9. Opens an interactive Zsh session.

No manual container configuration is required.

## Using DevBox

### Access the workspace

Once inside the DevBox:

```bash
cd /workspace
```

Your projects are available under this directory.

### Start a project

Navigate to a project directory:

```bash
cd /workspace/project-1
```

Start its containers:

```bash
docker compose up -d
```

The Network Manager automatically detects eligible project networks and connects the DevBox.

### Access project containers

Containers can be accessed through their Docker DNS names.

For example, to connect to a PostgreSQL container:

```bash
psql -h project-1-db -p 5432 -U appuser
```

You can also test connectivity using Python:

```bash
python3 -c "import socket; s=socket.create_connection(('project-1-db', 5432), timeout=5); print('Connection successful'); s.close()"
```

No manual IP configuration is required.

### Available tools

The DevBox image includes:

| Tool | Purpose |
|---|---|
| Git | Version control |
| Python 3 | Python development |
| pip / venv | Python package management |
| uv | Python project and dependency management |
| Docker CLI | Container management |
| Docker Compose | Multi-container applications |
| Terraform | Infrastructure as Code |
| Zsh | Interactive shell |
| Oh My Zsh | Shell customization |

## Network Manager

The Network Manager is responsible for automatic network discovery and synchronization.

It runs continuously inside the DevBox container.

### How it works

1. Lists Docker networks.
2. Identifies eligible networks.
3. Filters networks based on configuration.
4. Connects the DevBox to eligible networks.
5. Disconnects managed networks that are no longer eligible.
6. Repeats the process every 10 seconds.

By default, it only considers:

- Bridge networks.
- Docker Compose-managed networks.
- Networks that are not marked as internal.
- Networks with valid IPAM configuration.

### Network Manager logs

Inside the DevBox:

```bash
cat /tmp/network-manager.log
```

Follow logs in real time:

```bash
tail -f /tmp/network-manager.log
```

Check whether the process is running:

```bash
pgrep -af manager.py
```

## Stopping DevBox

To stop and remove DevBox resources, exit the container:

```bash
exit
```

Then, from the host, navigate to the DevBox directory and run:

```bash
./stop.sh
```

The stop script removes:

- DevBox container.
- DevBox Compose network.
- DevBox persistent home volume.
- Other orphaned containers belonging to the DevBox Compose project.

The following resources are preserved:

- Workspace directory and project files.
- Project containers.
- Project volumes and databases.
- Docker images.

## Rebuilding DevBox

To recreate the environment from scratch:

```bash
./stop.sh
./start.sh
```

The startup script rebuilds and starts the DevBox.

Your workspace remains untouched, allowing you to recreate the development environment without losing project data.

## Configuration

The `start.sh` script generates a `.env` file automatically.

The following variables are configured:

| Variable | Description |
|---|---|
| `USERNAME` | DevBox user |
| `USER_UID` | Host user ID |
| `USER_GID` | Host group ID |
| `DOCKER_GID` | Docker socket group ID |
| `TZ` | Host timezone |
| `WORKSPACE_PATH` | Absolute workspace path |

These values are detected automatically during startup.

## Troubleshooting

### Docker socket permission issues

Check the Docker socket:

```bash
ls -l /var/run/docker.sock
```

Verify Docker access inside the DevBox:

```bash
docker ps
```

### Network Manager is not running

Check the process:

```bash
pgrep -af manager.py
```

Inspect logs:

```bash
cat /tmp/network-manager.log
```

### Project container is unreachable

Verify the DevBox network connections from the host:

```bash
docker inspect devbox \
  --format '{{json .NetworkSettings.Networks}}'
```

Inspect the project network:

```bash
docker network ls
```

Check that the project network is a Docker Compose-managed bridge network.

## Important Notes

- DevBox uses the host Docker socket to manage containers. This provides extensive control over the host Docker Engine and should be treated as privileged access.
- Project containers and their volumes are managed independently by their respective Docker Compose configurations.
- The workspace is intentionally stored outside the DevBox project directory.
- Removing DevBox does not remove project data.
- The Network Manager only discovers networks that match its eligibility rules.