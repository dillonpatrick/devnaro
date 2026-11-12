"""Tests for declarative DevBox stack definitions."""

import pytest

from devbox_manager.stack_resolver import (
    StackDefinitionError,
    resolve_stack,
    validate_stack_definition,
    write_build_inputs,
)


def valid_definition(**overrides):
    definition = {
        "schema_version": 1,
        "name": "python-api",
        "description": "Python API development environment.",
        "packages": {"alpine": ["git", "jq"]},
        "tools": {
            "terraform": {"version": "1.17.1"},
            "uv": {"version": "0.13.7"},
        },
        "environment": {"APP_ENV": "development"},
    }
    definition.update(overrides)
    return definition


def test_validate_stack_definition_returns_normalized_values():
    stack = validate_stack_definition(valid_definition())
    assert stack.name == "python-api"
    assert stack.alpine_packages == ("git", "jq")
    assert stack.tools == {"terraform": "1.17.1", "uv": "0.13.7"}
    assert stack.environment == {"APP_ENV": "development"}


def test_build_inputs_are_deterministic_and_plain_data():
    definition = valid_definition(
        tools={"uv": {"version": "0.13.7"}, "terraform": {"version": "1.17.1"}},
        environment={"Z_LAST": "last", "A_FIRST": "first"},
    )
    result = validate_stack_definition(definition).to_build_inputs()
    assert list(result["tools"]) == ["terraform", "uv"]
    assert list(result["environment"]) == ["A_FIRST", "Z_LAST"]
    assert result["packages"] == {"alpine": ["git", "jq"]}


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"schema_version": True}, "schema_version"),
        ({"schema_version": 2}, "Unsupported schema_version"),
        ({"name": "Bad_Name"}, "name must contain"),
        ({"description": " "}, "description"),
        ({"packages": {"alpine": "git"}}, "packages.alpine must be a list"),
        ({"packages": {"alpine": ["git", "../etc"]}}, "Invalid package name"),
        ({"packages": {"alpine": ["git", "git"]}}, "Duplicate Alpine package"),
        ({"tools": {"node": {"version": "22"}}}, "Unsupported tool"),
        ({"tools": {"uv": {}}}, "version is required"),
        ({"tools": {"uv": {"version": "$LATEST"}}, "Invalid version"),
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
    definition = valid_definition(packages={"alpine": [], "apt": ["curl"]})
    with pytest.raises(StackDefinitionError, match="Unknown field"):
        validate_stack_definition(definition)


def test_resolve_stack_loads_yaml_and_checks_directory_name(tmp_path):
    stack_dir = tmp_path / "python-api"
    stack_dir.mkdir()
    stack_file = stack_dir / "stack.yaml"
    stack_file.write_text(
        """schema_version: 1
name: python-api
description: Python API development environment.
packages:
  alpine: [git, jq]
tools:
  uv:
    version: "0.13.7"
environment:
  APP_ENV: development
""",
        encoding="utf-8",
    )
    stack = resolve_stack(stack_file)
    assert stack.name == "python-api"
    assert stack.alpine_packages == ("git", "jq")


def test_resolve_stack_rejects_directory_name_mismatch(tmp_path):
    stack_dir = tmp_path / "expected-name"
    stack_dir.mkdir()
    stack_file = stack_dir / "stack.yaml"
    stack_file.write_text(
        """schema_version: 1
name: another-name
description: Example.
packages:
  alpine: []
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
        """schema_version: 1
name: duplicate
name: overwritten
description: Example.
packages:
  alpine: []
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

    assert (tmp_path / "alpine-packages.txt").read_text() == "git\njq\n"
    assert (tmp_path / "terraform-version").read_text() == "1.17.1\n"
    assert (tmp_path / "uv-version").read_text() == "0.13.7\n"
    assert (tmp_path / "stack-name").read_text() == "python-api\n"
    environment = (tmp_path / "environment.sh").read_text()
    assert "export APP_ENV='dev environment'" in environment
    assert "export APP_LABEL='it'\\''s ready'" in environment
