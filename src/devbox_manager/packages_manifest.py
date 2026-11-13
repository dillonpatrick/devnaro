"""Read and update the host-backed additional Debian package manifest."""

from pathlib import Path
import re

PACKAGE_MANIFEST_PATH = Path("/opt/devbox-config/packages.txt")
PACKAGE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9+_.-]+$")


class PackageManifestError(ValueError):
    """Raised when the additional package manifest cannot be updated."""


def validate_package_name(package: str) -> str:
    """Validate and normalize one Debian package name."""
    normalized = package.strip()
    if not normalized or not PACKAGE_NAME_PATTERN.fullmatch(normalized):
        raise PackageManifestError(
            f"Invalid package name: {package!r}. Use one package name."
        )
    return normalized


def read_manifest(path: Path = PACKAGE_MANIFEST_PATH) -> tuple[str, ...]:
    """Return package names, ignoring blank lines and full-line comments."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise PackageManifestError(
            f"Cannot read package manifest at {path}: {error}"
        ) from error

    packages: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        if len(entry.split()) != 1:
            raise PackageManifestError(
                f"Invalid manifest entry at line {line_number}: {line}"
            )
        packages.append(validate_package_name(entry))
    return tuple(packages)


def add_package(package: str, path: Path = PACKAGE_MANIFEST_PATH) -> bool:
    """Add a package to the manifest. Return False when it already exists."""
    normalized = validate_package_name(package)
    packages = read_manifest(path)
    if normalized in packages:
        return False

    try:
        content = path.read_text(encoding="utf-8")
        separator = "" if not content or content.endswith("\n") else "\n"
        path.write_text(
            f"{content}{separator}{normalized}\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise PackageManifestError(
            f"Cannot update package manifest at {path}: {error}"
        ) from error
    return True


def remove_package(package: str, path: Path = PACKAGE_MANIFEST_PATH) -> bool:
    """Remove a package from the manifest. Return False when absent."""
    normalized = validate_package_name(package)
    read_manifest(path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        remaining = [
            line for line in lines
            if line.strip() != normalized
        ]
        if len(remaining) == len(lines):
            return False
        path.write_text(
            "\n".join(remaining).rstrip("\n") + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise PackageManifestError(
            f"Cannot update package manifest at {path}: {error}"
        ) from error
    return True
