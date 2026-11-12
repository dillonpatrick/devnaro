"""Curated catalog of development tools supported by DevBox."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Metadata describing a tool supported by DevBox."""

    id: str
    name: str
    description: str
    category: str
    executable: str
    installer: str
    version: str | None = None


TOOL_CATALOG: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        id="terraform",
        name="Terraform",
        description="Infrastructure as Code tool for provisioning cloud resources.",
        category="Cloud",
        executable="terraform",
        installer="official_binary",
        version="1.17.1",
    ),
    ToolDefinition(
        id="python",
        name="Python",
        description="Programming language and runtime for automation and applications.",
        category="Languages",
        executable="python3",
        installer="alpine",
    ),
    ToolDefinition(
        id="uv",
        name="uv",
        description="Fast Python package and project manager.",
        category="Languages",
        executable="uv",
        installer="python_venv",
        version="0.13.7",
    ),
    ToolDefinition(
        id="docker-cli",
        name="Docker CLI",
        description="Command-line interface for managing Docker containers and images.",
        category="Containers",
        executable="docker",
        installer="alpine",
    ),
    ToolDefinition(
        id="git",
        name="Git",
        description="Distributed version control system.",
        category="Development",
        executable="git",
        installer="alpine",
    ),
    ToolDefinition(
        id="zsh",
        name="Zsh",
        description="Interactive shell with advanced customization features.",
        category="Shells",
        executable="zsh",
        installer="alpine",
    ),
    ToolDefinition(
        id="bash",
        name="Bash",
        description="GNU Bourne Again Shell.",
        category="Shells",
        executable="bash",
        installer="alpine",
    ),
)


def list_tools() -> tuple[ToolDefinition, ...]:
    """Return all tools in the catalog."""
    return TOOL_CATALOG


def search_tools(query: str) -> tuple[ToolDefinition, ...]:
    """Search tools by ID, name, description, or category."""
    normalized_query = query.strip().casefold()

    if not normalized_query:
        return ()

    return tuple(
        tool
        for tool in TOOL_CATALOG
        if normalized_query
        in " ".join(
            (tool.id, tool.name, tool.description, tool.category)
        ).casefold()
    )
