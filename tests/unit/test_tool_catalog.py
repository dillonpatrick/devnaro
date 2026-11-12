"""Unit tests for the curated development tool catalog."""

from devbox_manager.tool_catalog import TOOL_CATALOG, list_tools, search_tools


def test_catalog_contains_expected_tools():
    assert isinstance(TOOL_CATALOG, tuple)
    assert {tool.id for tool in TOOL_CATALOG} == {
        "terraform",
        "python",
        "uv",
        "docker-cli",
        "git",
        "zsh",
        "bash",
    }


def test_list_tools_returns_catalog():
    assert list_tools() is TOOL_CATALOG


def test_search_tools_matches_id_case_insensitively():
    results = search_tools("TERRAFORM")

    assert len(results) == 1
    assert results[0].id == "terraform"


def test_search_tools_matches_name():
    results = search_tools("Docker CLI")

    assert [tool.id for tool in results] == ["docker-cli"]


def test_search_tools_matches_description():
    results = search_tools("Infrastructure as Code")

    assert [tool.id for tool in results] == ["terraform"]


def test_search_tools_matches_category():
    results = search_tools("languages")

    assert {tool.id for tool in results} == {"python", "uv"}


def test_search_tools_ignores_surrounding_whitespace():
    assert search_tools("  git  ") == search_tools("git")


def test_search_tools_returns_empty_for_blank_query():
    assert search_tools("") == ()
    assert search_tools("   ") == ()
