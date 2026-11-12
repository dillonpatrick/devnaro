"""Search official Alpine Linux package repositories."""

from dataclasses import dataclass
from io import BytesIO
import platform
import tarfile
from urllib.error import URLError
from urllib.request import Request, urlopen

from pathlib import Path

ALPINE_MIRROR = "https://dl-cdn.alpinelinux.org/alpine"
REPOSITORIES = ("main", "community")
REQUEST_TIMEOUT = 12
MAX_RESULTS = 30


class AlpinePackageSearchError(RuntimeError):
    """Raised when Alpine package indexes cannot be retrieved or parsed."""


@dataclass(frozen=True, slots=True)
class AlpinePackage:
    """Package metadata published in an Alpine APKINDEX."""

    name: str
    version: str
    description: str
    repository: str
    architecture: str
    alpine_version: str


def _current_alpine_version() -> str:
    """Return the Alpine major.minor release configured by the running image."""
    try:
        release = Path("/etc/alpine-release").read_text(encoding="utf-8").strip()
    except OSError as error:
        raise AlpinePackageSearchError(
            "Could not determine the Alpine Linux release."
        ) from error

    parts = release.split(".")
    if len(parts) < 2 or not all(part.isdigit() for part in parts[:2]):
        raise AlpinePackageSearchError(f"Unrecognized Alpine release: {release!r}")

    return ".".join(parts[:2])


def _current_architecture() -> str:
    """Translate Python's machine identifier to Alpine's package architecture."""
    machine = platform.machine().lower()
    architectures = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
        "armv7l": "armv7",
        "armv6l": "armhf",
        "ppc64le": "ppc64le",
        "s390x": "s390x",
    }
    try:
        return architectures[machine]
    except KeyError as error:
        raise AlpinePackageSearchError(
            f"Unsupported Alpine package architecture: {machine}"
        ) from error


def _parse_index(
    content: bytes,
    repository: str,
    architecture: str,
    alpine_version: str,
) -> list[AlpinePackage]:
    """Parse package records from an APKINDEX file."""
    try:
        with tarfile.open(fileobj=BytesIO(content), mode="r:gz") as archive:
            index = archive.extractfile("APKINDEX")
            if index is None:
                raise AlpinePackageSearchError("The Alpine index has no APKINDEX file.")
            raw_index = index.read().decode("utf-8")
    except (tarfile.TarError, UnicodeDecodeError, OSError) as error:
        raise AlpinePackageSearchError("The Alpine package index is invalid.") from error

    packages: list[AlpinePackage] = []
    for record in raw_index.strip().split("\n\n"):
        fields: dict[str, str] = {}
        for line in record.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key] = value

        name = fields.get("P")
        if not name:
            continue

        packages.append(
            AlpinePackage(
                name=name,
                version=fields.get("V", "unknown"),
                description=fields.get("T", ""),
                repository=repository,
                architecture=fields.get("A", architecture),
                alpine_version=alpine_version,
            )
        )

    return packages


def _fetch_repository_index(
    alpine_version: str,
    architecture: str,
    repository: str,
) -> list[AlpinePackage]:
    """Download and parse one official Alpine repository index."""
    url = (
        f"{ALPINE_MIRROR}/v{alpine_version}/{repository}/"
        f"{architecture}/APKINDEX.tar.gz"
    )
    request = Request(url, headers={"User-Agent": "DevBox-tools-search/1.0"})

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            content = response.read()
    except (OSError, URLError) as error:
        raise AlpinePackageSearchError(
            f"Could not download the Alpine {repository} package index: {error}"
        ) from error

    return _parse_index(content, repository, architecture, alpine_version)


def search_alpine_packages(query: str) -> tuple[AlpinePackage, ...]:
    """Search official Alpine main and community repositories by name or description."""
    normalized_query = query.strip().casefold()
    if not normalized_query:
        return ()

    alpine_version = _current_alpine_version()
    architecture = _current_architecture()
    matches: dict[str, AlpinePackage] = {}

    for repository in REPOSITORIES:
        for package in _fetch_repository_index(
            alpine_version, architecture, repository
        ):
            searchable = f"{package.name} {package.description}".casefold()
            if normalized_query in searchable:
                matches.setdefault(package.name, package)

    ordered = sorted(
        matches.values(),
        key=lambda package: (
            not package.name.casefold().startswith(normalized_query),
            package.name.casefold(),
        ),
    )
    return tuple(ordered[:MAX_RESULTS])
