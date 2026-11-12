"""Rich-powered command line interface for DevBox."""

from datetime import datetime
import getpass
import os
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

from devbox_manager import __version__
from devbox_manager.config import WORKSPACE_PATH
from devbox_manager.docker_client import get_client, get_devbox_container
from devbox_manager.network_manager import process_status, read_logs
from devbox_manager.presentation import DEVBOX_THEME, configure_typer_help, render_panel
from devbox_manager.alpine_packages import AlpinePackageSearchError, search_alpine_packages
from devbox_manager.packages_manifest import (
    PackageManifestError,
    PACKAGE_MANIFEST_PATH,
    add_package,
    read_manifest,
    remove_package,
)
from typer.main import get_command

configure_typer_help()

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
tools_app = typer.Typer(
    help="Search Alpine packages and manage additional image packages.",
    no_args_is_help=True,
    cls=DevBoxTyperGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(tools_app, name="tools")



@tools_app.command("search")
def tools_search(query: str = typer.Argument(..., help="Text to search Alpine package names and descriptions.")) -> None:
    """Search official Alpine Linux repositories for available packages."""
    try:
        packages = search_alpine_packages(query)
    except AlpinePackageSearchError as error:
        render_panel(
            console,
            "Alpine package search failed",
            f"[error]{error}[/error]",
            border_style="error",
        )
        raise typer.Exit(code=1) from error

    table = Table(box=box.ROUNDED, header_style="heading")
    table.add_column("Package", style="info")
    table.add_column("Version")
    table.add_column("Repository")
    table.add_column("Description", overflow="fold")

    for package in packages:
        table.add_row(
            package.name,
            package.version,
            package.repository,
            package.description,
        )

    render_panel(
        console,
        "Alpine package search",
        table if packages else "[muted]No matching Alpine packages found.[/muted]",
        subtitle=f"{len(packages)} package(s) · Official Alpine main + community repositories",
    )


def _render_manifest_updated(action: str, package: str) -> None:
    """Explain that manifest changes require a host-side image recreation."""
    render_panel(
        console,
        "Package manifest updated",
        f"[success]{action} {package}.[/success]\n\n"
        "[warning]Changes take effect only after running this command on the host:[/warning]\n"
        "[accent]devbox recreate[/accent]",
    )


@tools_app.command("add")
def tools_add(package: str = typer.Argument(..., help="Alpine package name to add to the image.")) -> None:
    """Add an Alpine package to the image manifest."""
    try:
        changed = add_package(package, PACKAGE_MANIFEST_PATH)
    except PackageManifestError as error:
        render_panel(console, "Package manifest update failed", f"[error]{error}[/error]", border_style="error")
        raise typer.Exit(code=1) from error

    if changed:
        _render_manifest_updated("Added", package)
    else:
        render_panel(console, "Package already declared", f"[muted]{package} is already in the manifest.[/muted]")


@tools_app.command("remove")
def tools_remove(package: str = typer.Argument(..., help="Alpine package name to remove from the image.")) -> None:
    """Remove an Alpine package from the image manifest."""
    try:
        changed = remove_package(package, PACKAGE_MANIFEST_PATH)
    except PackageManifestError as error:
        render_panel(console, "Package manifest update failed", f"[error]{error}[/error]", border_style="error")
        raise typer.Exit(code=1) from error

    if changed:
        _render_manifest_updated("Removed", package)
    else:
        render_panel(
            console,
            "Package not declared",
            f"[warning]{package} is not present in the manifest.[/warning]",
        )
        raise typer.Exit(code=1)


@tools_app.command("list")
def tools_list() -> None:
    """List additional packages declared for the next image build."""
    try:
        packages = read_manifest(PACKAGE_MANIFEST_PATH)
    except PackageManifestError as error:
        render_panel(console, "Package manifest read failed", f"[error]{error}[/error]", border_style="error")
        raise typer.Exit(code=1) from error

    package_lines = (
        [f"[info]•[/info] {package}" for package in packages]
        if packages
        else ["[muted]No additional packages declared.[/muted]"]
    )
    package_lines.extend(
        [
            "",
            "[warning]Run on the host to apply changes:[/warning]",
            "[accent]devbox recreate[/accent]",
        ]
    )
    render_panel(
        console,
        "Additional image packages",
        "\n".join(package_lines),
        subtitle=f"{len(packages)} package(s)",
    )


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


def _additional_path_tools(known_names: set[str]) -> list[tuple[str, str]]:
    """Discover extra executables in non-core PATH directories."""
    core_directories = {"/bin", "/sbin", "/usr/bin", "/usr/sbin"}
    discovered: dict[str, str] = {}

    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        resolved_directory = str(Path(directory).resolve())
        if resolved_directory in core_directories:
            continue

        path = Path(resolved_directory)
        if not path.is_dir():
            continue

        try:
            entries = sorted(path.iterdir())
        except OSError:
            continue

        for entry in entries:
            try:
                if entry.name in known_names or not entry.is_file():
                    continue
                if not os.access(entry, os.X_OK):
                    continue
                discovered.setdefault(entry.name, str(entry))
            except OSError:
                continue

    return sorted(discovered.items())


def _display_tool_path(executable: str) -> str:
    """Prefer a home-relative path for tools installed under the user home."""
    resolved = Path(executable).resolve()
    try:
        relative = resolved.relative_to(Path.home().resolve())
        return f"~/{relative.as_posix()}"
    except ValueError:
        return str(resolved)


def _tool_source(executable: str) -> str:
    """Classify tools in the user's local bin directory separately."""
    resolved = Path(executable).resolve()
    user_bin = (Path.home() / ".local" / "bin").resolve()
    try:
        resolved.relative_to(user_bin)
        return "User"
    except ValueError:
        core_directories = {Path("/bin"), Path("/sbin"), Path("/usr/bin"), Path("/usr/sbin")}
        if resolved.parent in core_directories:
            return "Image"
        return "Custom PATH"


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
    summary.add_row("Stack", f"[value]DevBox[/value] v{__version__}")
    summary.add_row("Base", base_image)

    tools = Table(box=box.ROUNDED, header_style="heading")
    tools.add_column("Tool", style="info")
    tools.add_column("Path", overflow="fold")
    tools.add_column("Source", style="muted")

    known_tools = [
        ("Terraform", "terraform"),
        ("Docker CLI", "docker"),
        ("Docker Compose", "docker"),
        ("Python", "python3"),
        ("uv", "uv"),
        ("Git", "git"),
        ("Zsh", "zsh"),
        ("Bash", "bash"),
    ]
    reported: set[str] = {"devbox-manager"}
    discovered_tools: list[tuple[str, str, str]] = []

    for label, executable in known_tools:
        path = shutil.which(executable)
        if not path:
            discovered_tools.append(("-", label, "[warning]Not installed[/warning]"))
            continue

        discovered_tools.append((_tool_source(path), label, _display_tool_path(path)))
        reported.add(Path(path).name)

    oh_my_zsh = Path.home() / ".oh-my-zsh"
    if (oh_my_zsh / ".git").exists():
        discovered_tools.append(
            ("Image", "Oh My Zsh", str(oh_my_zsh.resolve()))
        )

    for name, executable in _additional_path_tools(reported):
        source = _tool_source(executable)
        discovered_tools.append((source, name, _display_tool_path(executable)))

    for source, name, path in sorted(
        discovered_tools,
        key=lambda item: (item[0].casefold(), item[1].casefold()),
    ):
        tools.add_row(name, path, source)

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
        subtitle="Image = core system paths · User = installed in ~/.local/bin · Custom PATH = discovered in other PATH directories · Host = external integration",
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
            border_style="error",
        )
        raise typer.Exit(code=1) from error

    attrs = container.attrs
    state = attrs.get("State", {})
    networks = attrs.get("NetworkSettings", {}).get("Networks", {})
    started = _format_started_at(state.get("StartedAt", ""))

    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column("Property", style="info", no_wrap=True)
    table.add_column("Value")

    state_label = (
        f"[success]{container.status}[/success]"
        if container.status == "running"
        else f"[warning]{container.status}[/warning]"
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
        "DevBox health check",
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
        usage = " ".join(("dm", *path, *arguments))
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
    details.add_row("DevBox version", f"[value]{__version__}[/value]")
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
        "DevBox Development Environment",
        content,
        border_style="info",
        padding=(1, 2),
    )


if __name__ == "__main__":
    app()
