"""Search Debian packages using the image's APT package indexes."""

from dataclasses import dataclass
import subprocess

MAX_RESULTS = 30
COMMAND_TIMEOUT = 10


class DebianPackageSearchError(RuntimeError):
    """Raised when the local Debian package indexes cannot be queried."""


@dataclass(frozen=True, slots=True)
class DebianPackage:
    """Package metadata returned by APT."""

    name: str
    version: str
    description: str
    repository: str = "Debian APT"


def _run_apt_cache(arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            ["apt-cache", *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=COMMAND_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DebianPackageSearchError(f"Could not query Debian package indexes: {error}") from error

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DebianPackageSearchError(detail or "apt-cache returned an error.")
    return result.stdout


def _package_details(name: str) -> DebianPackage | None:
    output = _run_apt_cache(["show", name])
    paragraphs = output.split("\n\n")
    for paragraph in paragraphs:
        fields: dict[str, str] = {}
        description_lines: list[str] = []
        in_description = False
        for line in paragraph.splitlines():
            if line.startswith(" ") and in_description:
                description_lines.append(line.strip())
            elif ": " in line:
                key, value = line.split(": ", 1)
                fields[key] = value
                in_description = key == "Description"
                if in_description:
                    description_lines.append(value)
        if fields.get("Package") == name:
            description = " ".join(description_lines).strip()
            return DebianPackage(
                name=name,
                version=fields.get("Version", "unknown"),
                description=description,
            )
    return None


def search_debian_packages(query: str) -> tuple[DebianPackage, ...]:
    """Search the Debian package indexes by package name or description."""
    normalized = query.strip()
    if not normalized:
        return ()
    output = _run_apt_cache(["search", normalized])
    names: list[str] = []
    for line in output.splitlines():
        if " - " not in line:
            continue
        name, _ = line.split(" - ", 1)
        if name and name not in names:
            names.append(name)

    packages = []
    for name in names[:MAX_RESULTS]:
        package = _package_details(name)
        if package is not None:
            packages.append(package)
    return tuple(packages)


def available_debian_packages(package_names: set[str] | tuple[str, ...]) -> frozenset[str]:
    """Return requested names that have an installable Debian package candidate."""
    requested = {name.strip() for name in package_names if name.strip()}
    available = set()
    for name in requested:
        if _package_details(name) is not None:
            available.add(name)
    return frozenset(available)
