"""Tests for the additional Debian package manifest."""

import pytest

from devbox_manager.packages_manifest import (
    PackageManifestError,
    add_package,
    read_manifest,
    remove_package,
    validate_package_name,
)


def test_read_manifest_ignores_comments_and_blank_lines(tmp_path):
    manifest = tmp_path / "packages.txt"
    manifest.write_text("# tools\n\njq\n  ripgrep  \n", encoding="utf-8")

    assert read_manifest(manifest) == ("jq", "ripgrep")


def test_add_package_appends_and_prevents_duplicates(tmp_path):
    manifest = tmp_path / "packages.txt"
    manifest.write_text("# tools\njq\n", encoding="utf-8")

    assert add_package("ripgrep", manifest) is True
    assert add_package("ripgrep", manifest) is False
    assert read_manifest(manifest) == ("jq", "ripgrep")
    assert manifest.read_text(encoding="utf-8") == "# tools\njq\nripgrep\n"


def test_add_package_creates_entry_in_empty_manifest(tmp_path):
    manifest = tmp_path / "packages.txt"
    manifest.write_text("", encoding="utf-8")

    assert add_package("tree", manifest) is True
    assert manifest.read_text(encoding="utf-8") == "tree\n"


def test_remove_package_preserves_comments_and_other_entries(tmp_path):
    manifest = tmp_path / "packages.txt"
    manifest.write_text("# tools\njq\nripgrep\ntree\n", encoding="utf-8")

    assert remove_package("ripgrep", manifest) is True
    assert remove_package("missing", manifest) is False
    assert manifest.read_text(encoding="utf-8") == "# tools\njq\ntree\n"


@pytest.mark.parametrize("package", ["", "two packages", "../jq", "jq;rm", "#comment", "jq\\nnodejs"])
def test_validate_package_name_rejects_invalid_values(package):
    with pytest.raises(PackageManifestError):
        validate_package_name(package)


@pytest.mark.parametrize("package", ["jq", "nodejs22", "py3.12", "lib+compat", "foo_bar", "foo-bar"])
def test_validate_package_name_accepts_debian_safe_names(package):
    assert validate_package_name(package) == package


def test_read_manifest_rejects_multiple_names_on_one_line(tmp_path):
    manifest = tmp_path / "packages.txt"
    manifest.write_text("jq ripgrep\n", encoding="utf-8")

    with pytest.raises(PackageManifestError, match="Invalid manifest entry"):
        read_manifest(manifest)
