"""Tests for declarative DevBox stack definitions."""

import shlex
from pathlib import Path

import pytest

from devbox_manager.stack_resolver import (
    StackDefinitionError,
    resolve_stack,
    validate_stack_definition,
    write_build_inputs,
)


def valid_definition(**overrides):
    definition = {
        "schema_version": 2,
        "name": "python-api",
        "description": "Python API development environment.",
        "base": {"distribution": "debian", "version": "trixie"},
        "packages": {"debian": ["git", "jq"]},
        "tools": {
            "terraform": {"channel": "stable"},
            "uv": {"version": "0.13.7"},
        },
        "environment": {"APP_ENV": "development"},
    }
    definition.update(overrides)
    return definition


def test_validate_stack_definition_returns_normalized_values():
    stack = validate_stack_definition(valid_definition())
    assert stack.name == "python-api"
    assert stack.distribution == "debian"
    assert stack.base_version == "trixie"
    assert stack.base_image == "debian:trixie-slim"
    assert stack.packages == {"debian": ("git", "jq")}
    assert stack.tools == {
        "terraform": {"channel": "stable"},
        "uv": {"version": "0.13.7"},
    }
    assert stack.environment == {"APP_ENV": "development"}


def test_debian_base_uses_slim_variant():
    definition = valid_definition(base={"distribution": "debian", "version": "trixie"})
    stack = validate_stack_definition(definition)
    assert stack.base_image == "debian:trixie-slim"


def test_build_inputs_are_deterministic_and_plain_data():
    definition = valid_definition(
        tools={"uv": {"channel": "stable"}, "terraform": {"version": "1.17.1"}},
        environment={"Z_LAST": "last", "A_FIRST": "first"},
    )
    result = validate_stack_definition(definition).to_build_inputs()
    assert list(result["tools"]) == ["terraform", "uv"]
    assert list(result["environment"]) == ["A_FIRST", "Z_LAST"]
    assert result["base"] == {
        "distribution": "debian",
        "version": "trixie",
        "image": "debian:trixie-slim",
    }
    assert result["packages"] == {
        "debian": ["git", "jq"],
    }


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"schema_version": True}, "schema_version"),
        ({"schema_version": 1}, "Unsupported schema_version"),
        ({"name": "Bad_Name"}, "name must contain"),
        ({"description": " "}, "description"),
        ({"base": {"distribution": "alpine", "version": "3.22"}}, "Unsupported base distribution"),
        ({"base": {"distribution": "debian"}}, "base.distribution and base.version are required"),
        ({"base": {"distribution": "debian", "version": "../latest"}}, "Invalid base version"),
        ({"packages": {"debian": "git"}}, "packages.debian must be a list"),
        ({"packages": {"debian": ["git", "../etc"]}}, "Invalid package name"),
        ({"packages": {"debian": ["git", "git"]}}, "Duplicate debian package"),
        ({"packages": {"apt": ["git"]}}, "Unknown field"),
        ({"tools": {"node": {"channel": "lts"}}}, "Unsupported tool"),
        ({"tools": {"uv": {}}}, "exactly one of version or channel"),
        ({"tools": {"uv": {"version": "0.13.7", "channel": "stable"}}}, "exactly one of version or channel"),
        ({"tools": {"uv": {"version": "$LATEST"}}}, "Invalid version"),
        ({"tools": {"uv": {"channel": "latest"}}}, "Unsupported channel"),
        ({"environment": {"lowercase": "value"}}, "Invalid environment variable"),
        ({"environment": {"APP_ENV": 1}}, "must be a string"),
        ({"environment": {"APP_ENV": "$HOME"}}, "unsupported expansion"),
        ({"unexpected": True}, "Unknown field"),
    ],
)
def test_validate_stack_definition_rejects_invalid_data(overrides, message):
    with pytest.raises(StackDefinitionError, match=message):
        validate_stack_definition(valid_definition(**overrides))


def test_rejects_missing_required_fields():
    definition = valid_definition()
    del definition["tools"]
    with pytest.raises(StackDefinitionError, match="Missing required"):
        validate_stack_definition(definition)


def test_rejects_unknown_nested_fields():
    definition = valid_definition(packages={"debian": [], "apt": ["curl"]})
    with pytest.raises(StackDefinitionError, match="Unknown field"):
        validate_stack_definition(definition)


def test_resolve_stack_loads_yaml_and_checks_directory_name(tmp_path):
    stack_dir = tmp_path / "python-api"
    stack_dir.mkdir()
    stack_file = stack_dir / "stack.yaml"
    stack_file.write_text(
        """schema_version: 2
name: python-api
description: Python API development environment.
base:
  distribution: debian
  version: "trixie"
packages:
  debian: [git, jq]
tools:
  uv:
    channel: stable
environment:
  APP_ENV: development
""",
        encoding="utf-8",
    )
    stack = resolve_stack(stack_file)
    assert stack.name == "python-api"
    assert stack.base_image == "debian:trixie-slim"
    assert stack.packages["debian"] == ("git", "jq")


def test_resolve_stack_rejects_directory_name_mismatch(tmp_path):
    stack_dir = tmp_path / "expected-name"
    stack_dir.mkdir()
    stack_file = stack_dir / "stack.yaml"
    stack_file.write_text(
        """schema_version: 2
name: another-name
description: Example.
base:
  distribution: debian
  version: "trixie"
packages:
  debian: []
tools: {}
environment: {}
""",
        encoding="utf-8",
    )
    with pytest.raises(StackDefinitionError, match="does not match directory name"):
        resolve_stack(stack_file)


def test_resolve_stack_rejects_duplicate_yaml_keys(tmp_path):
    stack_dir = tmp_path / "duplicate"
    stack_dir.mkdir()
    stack_file = stack_dir / "stack.yaml"
    stack_file.write_text(
        """schema_version: 2
name: duplicate
name: overwritten
description: Example.
base:
  distribution: debian
  version: "trixie"
packages:
  debian: []
tools: {}
environment: {}
""",
        encoding="utf-8",
    )
    with pytest.raises(StackDefinitionError, match="Duplicate YAML key"):
        resolve_stack(stack_file)


def test_resolve_stack_rejects_invalid_yaml(tmp_path):
    stack_dir = tmp_path / "broken"
    stack_dir.mkdir()
    stack_file = stack_dir / "stack.yaml"
    stack_file.write_text("schema_version: [", encoding="utf-8")
    with pytest.raises(StackDefinitionError, match="Invalid YAML"):
        resolve_stack(stack_file)


def test_write_build_inputs_creates_shell_safe_artifacts(tmp_path):
    stack = validate_stack_definition(
        valid_definition(environment={"APP_ENV": "dev environment", "APP_LABEL": "it's ready"})
    )
    write_build_inputs(stack, tmp_path)

    assert (tmp_path / "base-image").read_text() == "debian:trixie-slim\n"
    assert not (tmp_path / "alpine-packages.txt").exists()
    assert (tmp_path / "debian-packages.txt").read_text() == "git\njq\n"
    assert (tmp_path / "terraform-version").read_text() == "\n"
    assert (tmp_path / "terraform-channel").read_text() == "stable\n"
    assert (tmp_path / "uv-version").read_text() == "0.13.7\n"
    assert (tmp_path / "uv-channel").read_text() == "\n"
    assert (tmp_path / "stack-name").read_text() == "python-api\n"
    environment = (tmp_path / "environment.sh").read_text()
    assert "export APP_ENV='dev environment'" in environment
    expected_label = shlex.quote("it's ready")
    assert f"export APP_LABEL={expected_label}" in environment


def test_default_stack_does_not_include_terraform():
    stack_file = Path(__file__).resolve().parents[2] / "stacks" / "default" / "stack.yaml"
    stack = resolve_stack(stack_file)

    assert "terraform" not in stack.tools
    assert stack.tools == {"uv": {"version": "0.13.7"}}
