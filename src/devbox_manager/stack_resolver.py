"""Load, validate and normalize declarative DevBox stack definitions."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import sys
from typing import Any

import yaml

from devbox_manager.packages_manifest import (
    PackageManifestError,
    validate_package_name,
)

SCHEMA_VERSION = 2
SUPPORTED_DISTRIBUTIONS = frozenset({"debian"})
SUPPORTED_TOOLS = frozenset({"terraform", "uv"})
SUPPORTED_CHANNELS = frozenset({"lts", "stable"})
STACK_FILENAME = "stack.yaml"

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_TOOL_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_-]*$")
_ENVIRONMENT_KEY_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_BASE_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class StackDefinitionError(ValueError):
    """Raised when a stack definition cannot be loaded or validated."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    """Construct a mapping while rejecting duplicate keys."""
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as error:
            raise StackDefinitionError("YAML mapping keys must be hashable.") from error
        if duplicate:
            raise StackDefinitionError(f"Duplicate YAML key: {key!r}.")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True, slots=True)
class StackDefinition:
    """Validated, normalized stack configuration."""

    schema_version: int
    name: str
    description: str
    distribution: str
    base_version: str
    packages: dict[str, tuple[str, ...]]
    tools: dict[str, dict[str, str]]
    environment: dict[str, str]

    @property
    def base_image(self) -> str:
        """Return the minimal supported official base image reference."""
        return f"debian:{self.base_version}-slim"

    def to_build_inputs(self) -> dict[str, Any]:
        """Return a plain, deterministic structure suitable for build generation."""
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "base": {
                "distribution": self.distribution,
                "version": self.base_version,
                "image": self.base_image,
            },
            "packages": {
                distribution: list(packages)
                for distribution, packages in sorted(self.packages.items())
            },
            "tools": {
                name: dict(sorted(declaration.items()))
                for name, declaration in sorted(self.tools.items())
            },
            "environment": dict(sorted(self.environment.items())),
        }


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StackDefinitionError(f"{field} must be a mapping.")
    if any(not isinstance(key, str) for key in value):
        raise StackDefinitionError(f"{field} keys must be strings.")
    return value


def _reject_unknown_fields(value: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise StackDefinitionError(f"Unknown field(s) in {field}: {', '.join(unknown)}.")


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StackDefinitionError(f"{field} must be a non-empty string.")
    if value != value.strip():
        raise StackDefinitionError(f"{field} must not contain surrounding whitespace.")
    return value


def _validate_base(value: Any) -> tuple[str, str]:
    base = _require_mapping(value, "base")
    _reject_unknown_fields(base, {"distribution", "version"}, "base")
    if set(base) != {"distribution", "version"}:
        raise StackDefinitionError("base.distribution and base.version are required.")
    distribution = _require_non_empty_string(base["distribution"], "base.distribution")
    if distribution not in SUPPORTED_DISTRIBUTIONS:
        supported = ", ".join(sorted(SUPPORTED_DISTRIBUTIONS))
        raise StackDefinitionError(
            f"Unsupported base distribution '{distribution}'. Supported: {supported}."
        )
    version = _require_non_empty_string(base["version"], "base.version")
    if not _BASE_VERSION_PATTERN.fullmatch(version):
        raise StackDefinitionError(f"Invalid base version: {version!r}.")
    return distribution, version


def _validate_packages(value: Any) -> dict[str, tuple[str, ...]]:
    packages = _require_mapping(value, "packages")
    _reject_unknown_fields(packages, set(SUPPORTED_DISTRIBUTIONS), "packages")
    validated: dict[str, tuple[str, ...]] = {}
    for distribution, raw_packages in packages.items():
        if not isinstance(raw_packages, list):
            raise StackDefinitionError(f"packages.{distribution} must be a list.")
        normalized_packages: list[str] = []
        seen: set[str] = set()
        for package in raw_packages:
            if not isinstance(package, str):
                raise StackDefinitionError(
                    f"Every packages.{distribution} entry must be a string."
                )
            try:
                normalized = validate_package_name(package)
            except PackageManifestError as error:
                raise StackDefinitionError(str(error)) from error
            if normalized in seen:
                raise StackDefinitionError(
                    f"Duplicate {distribution} package in stack definition: {normalized}."
                )
            seen.add(normalized)
            normalized_packages.append(normalized)
        validated[distribution] = tuple(normalized_packages)
    return validated


def _validate_tools(value: Any) -> dict[str, dict[str, str]]:
    tools = _require_mapping(value, "tools")
    validated: dict[str, dict[str, str]] = {}
    for tool_name, declaration in tools.items():
        if tool_name not in SUPPORTED_TOOLS:
            supported = ", ".join(sorted(SUPPORTED_TOOLS))
            raise StackDefinitionError(
                f"Unsupported tool '{tool_name}'. Supported tools: {supported}."
            )
        tool = _require_mapping(declaration, f"tools.{tool_name}")
        _reject_unknown_fields(tool, {"version", "channel"}, f"tools.{tool_name}")
        if len(tool) != 1 or not ({"version", "channel"} & set(tool)):
            raise StackDefinitionError(
                f"tools.{tool_name} must declare exactly one of version or channel."
            )
        if "version" in tool:
            version = _require_non_empty_string(
                tool["version"], f"tools.{tool_name}.version"
            )
            if not _TOOL_VERSION_PATTERN.fullmatch(version):
                raise StackDefinitionError(
                    f"Invalid version for tools.{tool_name}: {version!r}."
                )
            validated[tool_name] = {"version": version}
        else:
            channel = _require_non_empty_string(
                tool["channel"], f"tools.{tool_name}.channel"
            )
            if channel not in SUPPORTED_CHANNELS:
                supported = ", ".join(sorted(SUPPORTED_CHANNELS))
                raise StackDefinitionError(
                    f"Unsupported channel '{channel}' for tools.{tool_name}. "
                    f"Supported channels: {supported}."
                )
            validated[tool_name] = {"channel": channel}
    return validated


def _validate_environment(value: Any) -> dict[str, str]:
    environment = _require_mapping(value, "environment")
    validated: dict[str, str] = {}
    for key, raw_value in environment.items():
        if not _ENVIRONMENT_KEY_PATTERN.fullmatch(key):
            raise StackDefinitionError(f"Invalid environment variable name: {key!r}.")
        if not isinstance(raw_value, str):
            raise StackDefinitionError(f"environment.{key} must be a string.")
        if any(character in raw_value for character in ("\x00", "\n", "\r", "$", "`")):
            raise StackDefinitionError(
                f"environment.{key} contains unsupported expansion or control characters."
            )
        validated[key] = raw_value
    return validated


def validate_stack_definition(
    data: Any, *, expected_name: str | None = None
) -> StackDefinition:
    """Validate parsed YAML data and return a normalized stack definition."""
    definition = _require_mapping(data, "Stack definition")
    _reject_unknown_fields(
        definition,
        {"schema_version", "name", "description", "base", "packages", "tools", "environment"},
        "stack definition",
    )
    required = {
        "schema_version", "name", "description", "base",
        "packages", "tools", "environment",
    }
    missing = sorted(required - set(definition))
    if missing:
        raise StackDefinitionError(f"Missing required field(s): {', '.join(missing)}.")

    schema_version = definition["schema_version"]
    if type(schema_version) is not int or schema_version != SCHEMA_VERSION:
        raise StackDefinitionError(
            f"Unsupported schema_version {schema_version!r}; expected {SCHEMA_VERSION}."
        )

    name = _require_non_empty_string(definition["name"], "name")
    if not _NAME_PATTERN.fullmatch(name):
        raise StackDefinitionError("name must contain lowercase letters, numbers and hyphens only.")
    if expected_name is not None and name != expected_name:
        raise StackDefinitionError(
            f"Stack name '{name}' does not match directory name '{expected_name}'."
        )
    description = _require_non_empty_string(definition["description"], "description")
    distribution, base_version = _validate_base(definition["base"])
    packages = _validate_packages(definition["packages"])
    tools = _validate_tools(definition["tools"])

    return StackDefinition(
        schema_version=schema_version,
        name=name,
        description=description,
        distribution=distribution,
        base_version=base_version,
        packages=packages,
        tools=tools,
        environment=_validate_environment(definition["environment"]),
    )


def resolve_stack(stack_file: Path) -> StackDefinition:
    """Load and validate a stack.yaml, enforcing its directory/name identity."""
    path = Path(stack_file)
    if path.name != STACK_FILENAME:
        raise StackDefinitionError(f"Stack definition file must be named {STACK_FILENAME}.")
    if not path.is_file():
        raise StackDefinitionError(f"Stack definition not found: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise StackDefinitionError(f"Cannot read stack definition at {path}: {error}") from error
    try:
        data = yaml.load(content, Loader=_UniqueKeySafeLoader)
    except StackDefinitionError:
        raise
    except yaml.YAMLError as error:
        raise StackDefinitionError(f"Invalid YAML in stack definition {path}: {error}") from error
    return validate_stack_definition(data, expected_name=path.parent.name)


def write_build_inputs(stack: StackDefinition, output_dir: Path) -> None:
    """Write normalized, shell-safe files consumed by the runtime image build."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "base-image").write_text(stack.base_image + "\n", encoding="utf-8")
    for distribution in sorted(SUPPORTED_DISTRIBUTIONS):
        packages = stack.packages.get(distribution, ())
        (output_dir / f"{distribution}-packages.txt").write_text(
            "".join(f"{package}\n" for package in packages),
            encoding="utf-8",
        )
    for tool in sorted(SUPPORTED_TOOLS):
        declaration = stack.tools.get(tool, {})
        (output_dir / f"{tool}-version").write_text(
            declaration.get("version", "") + "\n", encoding="utf-8"
        )
        (output_dir / f"{tool}-channel").write_text(
            declaration.get("channel", "") + "\n", encoding="utf-8"
        )
    environment_lines = [
        f"export {key}={shlex.quote(value)}"
        for key, value in sorted(stack.environment.items())
    ]
    (output_dir / "environment.sh").write_text(
        "\n".join(environment_lines) + ("\n" if environment_lines else ""),
        encoding="utf-8",
    )
    (output_dir / "stack-name").write_text(stack.name + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a DevBox stack for image building.")
    parser.add_argument("--stack-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        stack = resolve_stack(args.stack_file)
        write_build_inputs(stack, args.output_dir)
    except StackDefinitionError as error:
        print(f"Stack definition error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
