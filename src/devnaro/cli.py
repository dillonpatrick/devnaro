"""Rich-powered command line interface for DevNaro."""

from datetime import datetime
import getpass
import os
import re
import subprocess
from pathlib import Path

import typer
from docker.errors import DockerException, NotFound
from rich import box
from rich.console import Console, Group
from rich.table import Table
from rich.text import Text

from devnaro import __version__
from devnaro.config import WORKSPACE_PATH
from devnaro.docker_client import get_client, get_devnaro_container
from devnaro.network_manager import process_status, read_logs
from devnaro.port_forwarding import (
    CONFIG_FILE as PORT_FORWARD_CONFIG,
    add_forward,
    load_forwards,
    remove_forward,
)
from devnaro.presentation import DEVNARO_THEME, configure_typer_help, render_panel
from typer.main import get_command

configure_typer_help()

console = Console(theme=DEVNARO_THEME, highlight=False)


class DevNaroTyperGroup(typer.core.TyperGroup):
    """Keep built-in shell completion active without exposing setup flags in help."""

    def get_params(self, ctx):
        params = super().get_params(ctx)
        for param in params:
            if param.name in {"install_completion", "show_completion"}:
                param.hidden = True
        return params


app = typer.Typer(
    name="devnaro",
    help="Inspect and troubleshoot your DevNaro environment.",
    no_args_is_help=True,
    cls=DevNaroTyperGroup,
    invoke_without_command=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
network_app = typer.Typer(
    name="network-manager",
    help="Inspect the automatic Docker network manager.",
    no_args_is_help=True,
    cls=DevNaroTyperGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(network_app, name="network-manager")
ports_app = typer.Typer(
    help=(
        "Manage localhost TCP forwards to services in project Docker networks.\n\n"
        "Example: dvn ports add 8080 my-service 80"
    ),
    no_args_is_help=True,
)
app.add_typer(ports_app, name="ports")



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
            border_style="error",
        )
        raise typer.Exit(code=1) from error


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", is_eager=True, help="Show the CLI version and exit."
    ),
) -> None:
    """DevNaro command line tools."""
    if version:
        render_panel(
            console,
            "DevNaro Manager",
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


@app.command()
def info() -> None:
    """Show container identity and host integration status."""
    try:
        os_release = {}
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os_release[key] = value.strip('"')
        base_image = os_release.get("PRETTY_NAME", "Debian")
    except OSError:
        base_image = "Unknown"

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="muted", no_wrap=True)
    summary.add_column()
    summary.add_row("Stack", f"[value]DevNaro[/value] v{__version__}")
    summary.add_row("Base", base_image)
    summary.add_row("User", getpass.getuser())
    summary.add_row("Hostname", os.uname().nodename)
    summary.add_row("Workspace", str(WORKSPACE_PATH))

    host_tools = Table(box=box.SIMPLE, show_header=False)
    host_tools.add_column("Integration", style="info")
    host_tools.add_column("Status")
    try:
        docker_engine = _read_version(
            ["docker", "version", "--format", "{{.Server.Version}}"]
        )
    except OSError:
        docker_engine = "Not available"
    host_tools.add_row("Docker Engine", docker_engine,)

    code_socket = Path("/run/devnaro-host/code.sock")
    host_tools.add_row(
        "VS Code bridge",
        "[success]Available[/success]" if code_socket.exists() else "[warning]Not detected[/warning]",
    )

    client = _docker_connection()
    try:
        container = get_devnaro_container(client)
        container.reload()
    except NotFound as error:
        render_panel(console, "DevNaro status", "[error]DevNaro container was not found.[/error]", border_style="error")
        raise typer.Exit(code=1) from error

    attrs = container.attrs
    state = attrs.get("State", {})
    networks = attrs.get("NetworkSettings", {}).get("Networks", {})
    started = _format_started_at(state.get("StartedAt", ""))
    container_status = container.status
    state_label = (
        f"[success]{container_status}[/success]"
        if container_status == "running"
        else f"[warning]{container_status}[/warning]"
    )
    status_table = Table(box=box.ROUNDED, show_header=False)
    status_table.add_column("Property", style="info", no_wrap=True)
    status_table.add_column("Value")
    status_table.add_row("Container", container.name)
    status_table.add_row("Status", state_label)
    status_table.add_row("Image", attrs.get("Config", {}).get("Image", "unknown"))
    status_table.add_row("Started", started)
    status_table.add_row("Connected networks", str(len(networks)))
    status_table.add_row("Workspace", str(WORKSPACE_PATH))

    render_panel(
        console,
        "DevNaro info",
        Group(
            summary,
            Text("HOST INTEGRATIONS", style="heading"),
            host_tools,
            Text("CONTAINER STATUS", style="heading"),
            status_table,
        ),
        subtitle=f"Container {container_status}",
    )



@ports_app.command("add")
def ports_add(
    local_port: int = typer.Argument(..., help="Port to listen on inside DevNaro localhost."),
    target_host: str = typer.Argument(..., help="Docker service or container name."),
    target_port: int = typer.Argument(..., help="Port exposed by the target service."),
) -> None:
    """Forward a DevNaro localhost port to a project service.

    Example:
        dvn ports add 8080 my-service 80
    """
    try:
        add_forward(local_port, target_host, target_port)
    except (OSError, ValueError) as error:
        render_panel(console, "Port forward not added", f"[error]{error}[/error]", border_style="error")
        raise typer.Exit(code=1) from error
    render_panel(
        console,
        "Port forward added",
        f"[success]localhost:{local_port} → {target_host}:{target_port}[/success]\n"
        "The Port Forwarding Manager applies this change automatically.",
    )


@ports_app.command("list")
def ports_list() -> None:
    """List configured localhost TCP forwards."""
    try:
        forwards = load_forwards()
    except ValueError as error:
        render_panel(console, "Port forwarding configuration error", f"[error]{error}[/error]", border_style="error")
        raise typer.Exit(code=1) from error
    table = Table(box=box.ROUNDED, header_style="heading")
    table.add_column("Local address", style="info")
    table.add_column("Target")
    for item in forwards:
        table.add_row(f"127.0.0.1:{item.local_port}", f"{item.target_host}:{item.target_port}")
    render_panel(
        console,
        "Configured port forwards",
        table if forwards else "[muted]No port forwards configured.[/muted]",
        subtitle=str(PORT_FORWARD_CONFIG),
    )


@ports_app.command("remove")
def ports_remove(
    local_port: int = typer.Argument(..., help="Local port to stop forwarding."),
) -> None:
    """Remove a localhost TCP forward."""
    try:
        removed = remove_forward(local_port)
    except (OSError, ValueError) as error:
        render_panel(console, "Port forward not removed", f"[error]{error}[/error]", border_style="error")
        raise typer.Exit(code=1) from error
    if not removed:
        render_panel(console, "Port forward not found", f"[warning]No forward uses local port {local_port}.[/warning]")
        raise typer.Exit(code=1)
    render_panel(console, "Port forward removed", f"[success]localhost:{local_port} will no longer be forwarded.[/success]")


@app.command()
def networks() -> None:
    """List Docker networks currently connected to DevNaro."""
    client = _docker_connection()

    try:
        container = get_devnaro_container(client)
        container.reload()
    except NotFound as error:
        render_panel(
            console,
            "DevNaro networks",
            "[error]DevNaro container was not found.[/error]",
            border_style="error",
        )
        raise typer.Exit(code=1) from error

    attached = container.attrs.get("NetworkSettings", {}).get("Networks", {})
    table = Table(box=box.ROUNDED, header_style="heading")
    table.add_column("Network", style="info")
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
            "DevNaro networks",
            "[warning]DevNaro is not connected to any networks.[/warning]",
            subtitle="0 networks connected",
        )
    else:
        render_panel(
            console,
            "DevNaro networks",
            table,
            subtitle=f"{len(attached)} network(s) connected",
        )


@app.command()
def doctor() -> None:
    """Run basic health checks for the DevNaro environment."""
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
            container = get_devnaro_container(client)
            container.reload()
            running = container.status == "running"
            checks.append(
                ("DevNaro container", running, container.status)
            )
        except NotFound:
            checks.append(("DevNaro container", False, "Container not found"))

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
    table.add_column("Check", style="info")
    table.add_column("Result")
    table.add_column("Details")

    for name, passed, details in checks:
        result = "[success]PASS[/success]" if passed else "[error]FAIL[/error]"
        table.add_row(name, result, details)

    passed_count = sum(1 for _, passed, _ in checks if passed)
    failed_count = len(checks) - passed_count
    content = (
        Group(table, Text("All checks passed.", style="success"))
        if failed_count == 0
        else table
    )
    render_panel(
        console,
        "DevNaro health check",
        content,
        subtitle=f"{passed_count} passed · {failed_count} failed",
    )

    if failed_count:
        raise typer.Exit(code=1)


@network_app.command("status")
def network_manager_status() -> None:
    """Show whether the Network Manager process is running."""
    running, details = process_status()

    if running and isinstance(details, list):
        table = Table(box=box.ROUNDED, show_header=True, header_style="heading")
        table.add_column("PID", style="info", justify="right")
        table.add_column("PPID", style="info", justify="right")
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
            ("● ", "success"),
            ("Running", "success"),
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
            border_style="error",
        )
        raise typer.Exit(code=1) from error

    render_panel(
        console,
        "Network Manager logs",
        content or "[muted]Log file is empty.[/muted]",
        subtitle=f"Last {lines} lines",
    )


def _registered_cli_commands(command=None, prefix: tuple[str, ...] = ()):
    """Yield command usage and help directly from the registered Typer command tree."""
    command = command or get_command(app)
    for name, child in command.commands.items():
        path = (*prefix, name)
        if getattr(child, "hidden", False):
            continue

        nested_commands = getattr(child, "commands", None)
        if nested_commands:
            yield from _registered_cli_commands(child, path)
            continue

        arguments = [
            parameter.name.upper()
            for parameter in child.params
            if parameter.__class__.__name__.endswith("Argument")
        ]
        usage = " ".join(("dvn", *path, *arguments))
        description = child.help or child.short_help or ""
        yield usage, description


def _completion_candidates(words: list[str]) -> list[str]:
    """Return command names and options from the registered Typer command tree."""
    command = get_command(app)
    consumed: list[str] = []

    while words:
        current = words[0]
        commands = getattr(command, "commands", None)
        if not commands:
            break

        if current in commands:
            consumed.append(current)
            command = commands[current]
            words = words[1:]
            continue

        return sorted(
            name
            for name, child in commands.items()
            if not getattr(child, "hidden", False)
            and name != "__complete"
            and name.startswith(current)
        )

    if getattr(command, "commands", None):
        return sorted(
            name
            for name, child in command.commands.items()
            if not getattr(child, "hidden", False) and name != "__complete"
        )

    return sorted(
        option
        for parameter in command.params
        for option in getattr(parameter, "opts", [])
        if option.startswith(words[0] if words else "")
    )


@app.command("__complete", hidden=True, context_settings={
    "allow_extra_args": True,
    "ignore_unknown_options": True,
})
def _complete(ctx: typer.Context) -> None:
    """Internal completion endpoint consumed by the Zsh integration."""
    for candidate in _completion_candidates(list(ctx.args)):
        typer.echo(candidate)


@app.command()
def welcome() -> None:
    """Display the DevNaro welcome screen."""
    manager_running, _ = process_status()
    try:
        os_release = {}
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os_release[key] = value.strip('"')
        base_release = os_release.get("PRETTY_NAME", "Debian")
    except OSError:
        base_release = "unknown"

    details = Table.grid(padding=(0, 2))
    details.add_column(style="muted", width=18, no_wrap=True)
    details.add_column()
    details.add_row("DevNaro version", f"[value]{__version__}[/value]")
    details.add_row("Base image", base_release)
    details.add_row("User", getpass.getuser())
    details.add_row("Workspace", str(Path.cwd()))
    details.add_row("Home", str(Path.home()))
    manager_status = "[success]Running[/success]" if manager_running else "[warning]Not detected[/warning]"
    details.add_row("Network Manager", manager_status)

    commands = Table.grid(padding=(0, 2))
    commands.add_column(style="accent", no_wrap=True)
    commands.add_column(style="muted")
    commands.add_row("code .", "Open current project in VS Code")
    for command_usage, description in _registered_cli_commands():
        commands.add_row(command_usage, description)
    commands.add_row("docker ps", "Running containers")
    commands.add_row("docker compose up -d", "Start project services")

    content = Group(
        details,
        Text("QUICK COMMANDS · INSIDE CONTAINER", style="heading"),
        commands,
    )
    render_panel(
        console,
        "DevNaro Development Environment",
        content,
        border_style="info",
        padding=(1, 2),
    )


if __name__ == "__main__":
    app()
