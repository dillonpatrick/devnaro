"""Rich-powered command line interface for DevBox."""

from datetime import datetime
import re
from pathlib import Path

import typer
from docker.errors import DockerException, NotFound
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devbox_manager import __version__
from devbox_manager.config import WORKSPACE_PATH
from devbox_manager.docker_client import get_client, get_devbox_container
from devbox_manager.network_manager import process_status, read_logs

console = Console()
app = typer.Typer(
    name="devbox-manager",
    help="Inspect and troubleshoot your DevBox environment.",
    no_args_is_help=True,
    invoke_without_command=True,
    rich_markup_mode="rich",
)
network_app = typer.Typer(
    name="network-manager",
    help="Inspect the automatic Docker network manager.",
    no_args_is_help=True,
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
        console.print(
            Panel(
                f"[red]Unable to connect to Docker:[/red]\n{error}",
                title="Docker connection failed",
                border_style="red",
            )
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
        console.print(f"DevBox Manager [cyan]v{__version__}[/cyan]")
        raise typer.Exit()


@app.command()
def status() -> None:
    """Show the DevBox container status and runtime details."""
    client = _docker_connection()

    try:
        container = get_devbox_container(client)
        container.reload()
    except NotFound as error:
        console.print("[red]DevBox container was not found.[/red]")
        raise typer.Exit(code=1) from error

    attrs = container.attrs
    state = attrs.get("State", {})
    networks = attrs.get("NetworkSettings", {}).get("Networks", {})
    started = _format_started_at(state.get("StartedAt", ""))

    table = Table(title="DevBox status", box=box.ROUNDED, show_header=False)
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

    console.print(table)

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
        console.print("[red]DevBox container was not found.[/red]")
        raise typer.Exit(code=1) from error

    attached = container.attrs.get("NetworkSettings", {}).get("Networks", {})
    table = Table(title="DevBox networks", box=box.ROUNDED)
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
        console.print("[yellow]DevBox is not connected to any networks.[/yellow]")
    else:
        console.print(table)


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
    checks.append(
        (
            "Network Manager",
            manager_running,
            manager_details.splitlines()[0] if manager_details else "Process not running",
        )
    )

    table = Table(title="DevBox health check", box=box.ROUNDED)
    table.add_column("Check", style="cyan")
    table.add_column("Result")
    table.add_column("Details")

    for name, passed, details in checks:
        result = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        table.add_row(name, result, details)

    console.print(table)

    if not all(passed for _, passed, _ in checks):
        raise typer.Exit(code=1)

    console.print(Panel("[bold green]All checks passed.[/bold green]", border_style="green"))


@network_app.command("status")
def network_manager_status() -> None:
    """Show whether the Network Manager process is running."""
    running, details = process_status()

    if running:
        console.print(Panel(details, title="Network Manager", border_style="green"))
    else:
        console.print(
            Panel(
                "[yellow]Network Manager is not running.[/yellow]",
                title="Network Manager",
                border_style="yellow",
            )
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
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error

    console.print(
        Panel(
            content or "[dim]Log file is empty.[/dim]",
            title=f"Network Manager logs (last {lines} lines)",
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    app()
