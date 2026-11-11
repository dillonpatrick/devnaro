"""Rich-powered command line interface for DevBox."""

from datetime import datetime
import getpass
import re
import shutil
import subprocess
from pathlib import Path

import typer
from docker.errors import DockerException, NotFound
from rich import box
from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from devbox_manager import __version__
from devbox_manager.config import WORKSPACE_PATH
from devbox_manager.docker_client import get_client, get_devbox_container
from devbox_manager.network_manager import process_status, read_logs
from devbox_manager.presentation import configure_typer_help, render_panel

configure_typer_help()

DEVBOX_THEME = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "muted": "dim",
        "heading": "bold bright_cyan",
        "accent": "bold green",
    }
)
console = Console(theme=DEVBOX_THEME, highlight=False)


class DevBoxTyperGroup(typer.core.TyperGroup):
    """Keep built-in shell completion active without exposing setup flags in help."""

    def get_params(self, ctx):
        params = super().get_params(ctx)
        for param in params:
            if param.name in {"install_completion", "show_completion"}:
                param.hidden = True
        return params


app = typer.Typer(
    name="devbox-manager",
    help="Inspect and troubleshoot your DevBox environment.",
    no_args_is_help=True,
    cls=DevBoxTyperGroup,
    invoke_without_command=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
network_app = typer.Typer(
    name="network-manager",
    help="Inspect the automatic Docker network manager.",
    no_args_is_help=True,
    cls=DevBoxTyperGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(network_app, name="network-manager")


def _format_started_at(value: str) -> str:
    """Format Docker's RFC3339 timestamp, trimming nanoseconds to microseconds."""
    if not value or value.startswith("0001-"):
        return "Not running"

    normalized = value.replace("Z", "+00:00")
    normalized = re.sub(
        r"(\.\d{6})\d+(?=[+-]\d{2}:\d{2}$)",
        r"\1",
        normalized,
    )

    return datetime.fromisoformat(normalized).astimezone().strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )


def _docker_connection():
    try:
        client = get_client()
        client.ping()
        return client
    except DockerException as error:
        render_panel(
            console,
            "Docker connection failed",
            f"[error]Unable to connect to Docker:[/error]\n{error}",
            border_style="red",
        )
        raise typer.Exit(code=1) from error


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", is_eager=True, help="Show the CLI version and exit."
    ),
) -> None:
    """DevBox command line tools."""
    if version:
        render_panel(
            console,
            "DevBox Manager",
            f"[accent]v{__version__}[/accent]",
        )
        raise typer.Exit()


def _read_version(command: list[str]) -> str:
    """Return the first useful version line for an installed executable."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "Version unavailable"

    if result.returncode != 0:
        return "Version unavailable"

    output = (result.stdout or result.stderr).strip()
    if not output:
        return "Version unavailable"

    return output.splitlines()[0].strip()


def _tool_source(executable: str) -> str:
    """Classify tools in the user's local bin directory separately."""
    resolved = Path(executable).resolve()
    user_bin = (Path.home() / ".local" / "bin").resolve()
    try:
        resolved.relative_to(user_bin)
        return "User"
    except ValueError:
        return "Image"


@app.command()
def info() -> None:
    """Show the DevBox stack, base image, and installed development tools."""
    try:
        alpine_version = Path("/etc/alpine-release").read_text(encoding="utf-8").strip()
        base_image = f"Alpine Linux {alpine_version}"
    except OSError:
        base_image = "Unknown"

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="muted", no_wrap=True)
    summary.add_column()
    summary.add_row("Stack", f"[bold white]DevBox[/bold white] v{__version__}")
    summary.add_row("Base", base_image)

    tools = Table(box=box.ROUNDED, header_style="heading")
    tools.add_column("Tool", style="cyan")
    tools.add_column("Version")
    tools.add_column("Source", style="muted")

    known_tools = [
        ("Terraform", "terraform", ["version"]),
        ("Docker CLI", "docker", ["--version"]),
        ("Docker Compose", "docker", ["compose", "version", "--short"]),
        ("Python", "python3", ["--version"]),
        ("uv", "uv", ["--version"]),
        ("Git", "git", ["--version"]),
        ("Zsh", "zsh", ["--version"]),
        ("Bash", "bash", ["--version"]),
    ]
    reported: set[str] = set()

    for label, executable, arguments in known_tools:
        path = shutil.which(executable)
        if not path:
            tools.add_row(label, "[warning]Not installed[/warning]", "-")
            continue
        tools.add_row(
            label,
            _read_version([path, *arguments]),
            _tool_source(path),
        )
        reported.add(Path(path).name)

    oh_my_zsh = Path.home() / ".oh-my-zsh"
    if (oh_my_zsh / ".git").exists():
        commit = _read_version(["git", "-C", str(oh_my_zsh), "rev-parse", "--short", "HEAD"])
        tools.add_row("Oh My Zsh", commit, "Image")

    user_bin = Path.home() / ".local" / "bin"
    if user_bin.is_dir():
        for executable in sorted(user_bin.iterdir()):
            if not executable.is_file() or not executable.stat().st_mode & 0o111:
                continue
            if executable.name in reported:
                continue
            tools.add_row(
                executable.name,
                _read_version([str(executable), "--version"]),
                "User",
            )

    host_tools = Table(box=box.SIMPLE, show_header=False)
    host_tools.add_column("Integration", style="cyan")
    host_tools.add_column("Status")
    try:
        docker_engine = _read_version(
            ["docker", "version", "--format", "{{.Server.Version}}"]
        )
    except OSError:
        docker_engine = "Not available"
    host_tools.add_row("Docker Engine", docker_engine,)

    code_socket = Path("/run/devbox-host/code.sock")
    host_tools.add_row(
        "VS Code bridge",
        "[success]Available[/success]" if code_socket.exists() else "[warning]Not detected[/warning]",
    )

    render_panel(
        console,
        "DevBox info",
        Group(
            summary,
            Text("INSTALLED TOOLS", style="heading"),
            tools,
            Text("HOST INTEGRATIONS", style="heading"),
            host_tools,
        ),
        subtitle="Image = provided by DevBox · User = installed in ~/.local/bin · Host = external integration",
    )


@app.command()
def status() -> None:
    """Show the DevBox container status and runtime details."""
    client = _docker_connection()

    try:
        container = get_devbox_container(client)
        container.reload()
    except NotFound as error:
        render_panel(
            console,
            "DevBox status",
            "[error]DevBox container was not found.[/error]",
            border_style="red",
        )
        raise typer.Exit(code=1) from error

    attrs = container.attrs
    state = attrs.get("State", {})
    networks = attrs.get("NetworkSettings", {}).get("Networks", {})
    started = _format_started_at(state.get("StartedAt", ""))

    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value")

    state_label = (
        f"[green]{container.status}[/green]"
        if container.status == "running"
        else f"[yellow]{container.status}[/yellow]"
    )
    table.add_row("Container", container.name)
    table.add_row("Status", state_label)
    table.add_row("Image", attrs.get("Config", {}).get("Image", "unknown"))
    table.add_row("Started", started)
    table.add_row("Connected networks", str(len(networks)))
    table.add_row("Workspace", str(WORKSPACE_PATH))

    render_panel(
        console,
        "DevBox status",
        table,
        
        subtitle=f"Container {container.status}",
    )

    if container.status != "running":
        raise typer.Exit(code=1)


@app.command()
def networks() -> None:
    """List Docker networks currently connected to DevBox."""
    client = _docker_connection()

    try:
        container = get_devbox_container(client)
        container.reload()
    except NotFound as error:
        render_panel(
            console,
            "DevBox networks",
            "[error]DevBox container was not found.[/error]",
            border_style="red",
        )
        raise typer.Exit(code=1) from error

    attached = container.attrs.get("NetworkSettings", {}).get("Networks", {})
    table = Table(box=box.ROUNDED, header_style="heading")
    table.add_column("Network", style="cyan")
    table.add_column("Driver")
    table.add_column("Compose project")
    table.add_column("IP address")
    table.add_column("Internal")

    for name, details in sorted(attached.items()):
        try:
            network = client.networks.get(name)
            network.reload()
            attrs = network.attrs
            labels = attrs.get("Labels") or {}
            table.add_row(
                name,
                attrs.get("Driver", "unknown"),
                labels.get("com.docker.compose.project", "-"),
                details.get("IPAddress") or "-",
                "yes" if attrs.get("Internal") else "no",
            )
        except NotFound:
            table.add_row(name, "unknown", "-", details.get("IPAddress") or "-", "-")

    if not attached:
        render_panel(
            console,
            "DevBox networks",
            "[warning]DevBox is not connected to any networks.[/warning]",
            subtitle="0 networks connected",
        )
    else:
        render_panel(
            console,
            "DevBox networks",
            table,
            subtitle=f"{len(attached)} network(s) connected",
        )


@app.command()
def doctor() -> None:
    """Run basic health checks for the DevBox environment."""
    checks: list[tuple[str, bool, str]] = []

    socket_path = Path("/var/run/docker.sock")
    checks.append(
        (
            "Docker socket",
            socket_path.exists(),
            str(socket_path) if socket_path.exists() else "Not found",
        )
    )

    try:
        client = get_client()
        client.ping()
        checks.append(("Docker API", True, "Connection successful"))
    except DockerException as error:
        checks.append(("Docker API", False, str(error)))
        client = None

    if client is not None:
        try:
            container = get_devbox_container(client)
            container.reload()
            running = container.status == "running"
            checks.append(
                ("DevBox container", running, container.status)
            )
        except NotFound:
            checks.append(("DevBox container", False, "Container not found"))

    workspace_ok = WORKSPACE_PATH.is_dir()
    checks.append(
        (
            "Workspace",
            workspace_ok,
            str(WORKSPACE_PATH) if workspace_ok else "Directory not found",
        )
    )

    manager_running, manager_details = process_status()
    manager_summary = (
        f"Running (PID {manager_details[0].pid})"
        if manager_running and isinstance(manager_details, list)
        else str(manager_details)
    )
    checks.append(("Network Manager", manager_running, manager_summary))

    table = Table(box=box.ROUNDED, header_style="heading")
    table.add_column("Check", style="cyan")
    table.add_column("Result")
    table.add_column("Details")

    for name, passed, details in checks:
        result = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        table.add_row(name, result, details)

    passed_count = sum(1 for _, passed, _ in checks if passed)
    failed_count = len(checks) - passed_count
    render_panel(
        console,
        "DevBox health check",
        table,
        subtitle=f"{passed_count} passed · {failed_count} failed",
    )

    if not all(passed for _, passed, _ in checks):
        raise typer.Exit(code=1)

    render_panel(
        console,
        "Health check result",
        "[success]All checks passed.[/success]",
    )


@network_app.command("status")
def network_manager_status() -> None:
    """Show whether the Network Manager process is running."""
    running, details = process_status()

    if running and isinstance(details, list):
        table = Table(box=box.ROUNDED, show_header=True, header_style="heading")
        table.add_column("PID", style="bold cyan", justify="right")
        table.add_column("PPID", style="cyan", justify="right")
        table.add_column("User")
        table.add_column("State")
        table.add_column("Uptime")
        table.add_column("Command", overflow="fold")
        for process in details:
            table.add_row(
                str(process.pid),
                str(process.ppid),
                process.user,
                process.state,
                process.elapsed,
                process.command,
            )
        summary = Text.assemble(
            ("● ", "bold green"),
            ("Running", "bold green"),
            ("  Process ID (PID) uniquely identifies this running process.", "muted"),
        )
        legend = Text(
            "PID = process ID  •  PPID = parent process ID  •  "
            "User = account running it  •  Uptime = time since it started\n"
            "State: S = sleeping/waiting (normal while idle); R = running; "
            "D = uninterruptible wait; Z = zombie.",
            style="muted",
        )
        render_panel(
            console,
            "Network Manager",
            Group(summary, table, legend),
            subtitle=f"{len(details)} process(es) found",
        )
    else:
        render_panel(
            console,
            "Network Manager",
            f"[warning]Network Manager is not running.[/warning]\n\n[muted]{details}[/muted]",
        )
        raise typer.Exit(code=1)


@network_app.command("logs")
def network_manager_logs(
    lines: int = typer.Option(50, "--lines", "-n", min=1, max=1000),
) -> None:
    """Display recent Network Manager logs."""
    try:
        content = read_logs(lines=lines)
    except (FileNotFoundError, OSError) as error:
        render_panel(
            console,
            "Network Manager logs",
            f"[error]{error}[/error]",
            border_style="red",
        )
        raise typer.Exit(code=1) from error

    render_panel(
        console,
        "Network Manager logs",
        content or "[muted]Log file is empty.[/muted]",
        subtitle=f"Last {lines} lines",
    )


@app.command()
def welcome() -> None:
    """Display the DevBox welcome screen."""
    manager_running, _ = process_status()
    try:
        alpine_version = Path("/etc/alpine-release").read_text(encoding="utf-8").strip()
        alpine_version = ".".join(alpine_version.split(".")[:2])
    except OSError:
        alpine_version = "unknown"

    details = Table.grid(padding=(0, 2))
    details.add_column(style="muted", width=18, no_wrap=True)
    details.add_column()
    details.add_row("DevBox version", f"[bold white]{__version__}[/bold white]")
    details.add_row("Base image", f"Alpine Linux {alpine_version}")
    details.add_row("User", getpass.getuser())
    details.add_row("Workspace", str(Path.cwd()))
    details.add_row("Home", str(Path.home()))
    manager_status = "[success]Running[/success]" if manager_running else "[warning]Not detected[/warning]"
    details.add_row("Network Manager", manager_status)

    commands = Table.grid(padding=(0, 2))
    commands.add_column(style="accent", no_wrap=True)
    commands.add_column(style="muted")
    commands.add_row("code .", "Open current project in VS Code")
    commands.add_row("dm info", "DevBox stack and installed tools")
    commands.add_row("dm status", "Container status")
    commands.add_row("dm doctor", "Environment health checks")
    commands.add_row("dm networks", "Docker networks")
    commands.add_row("dm network-manager status", "Network Manager status")
    commands.add_row("dm network-manager logs", "Network Manager logs")
    commands.add_row("docker ps", "Running containers")
    commands.add_row("docker compose up -d", "Start project services")

    content = Group(
        details,
        Text("QUICK COMMANDS", style="heading"),
        commands,
        Text("Tip: run commands from inside each project directory.", style="muted"),
    )
    render_panel(
        console,
        "[bold green]DEVBOX[/bold green] [bold white]DEVELOPMENT ENVIRONMENT[/bold white]",
        content,
        border_style="bright_cyan",
        padding=(1, 2),
        expand=True,
    )


if __name__ == "__main__":
    app()
