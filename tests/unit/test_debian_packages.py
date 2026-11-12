"""Unit tests for Debian APT package discovery."""

import subprocess

import pytest

from devbox_manager import debian_packages
from devbox_manager.debian_packages import DebianPackageSearchError


def test_search_debian_packages_returns_matching_package_metadata(monkeypatch):
    def run(command, **kwargs):
        if command[1:3] == ["search", "git"]:
            return subprocess.CompletedProcess(command, 0, "git - fast, scalable, distributed revision control system\ngit-lfs - Git extension for versioning large files\n", "")
        if command[1:3] == ["show", "git"]:
            return subprocess.CompletedProcess(command, 0, "Package: git\nVersion: 1:2.47.3-0+deb13u1\nDescription: fast, scalable, distributed revision control system\n", "")
        if command[1:3] == ["show", "git-lfs"]:
            return subprocess.CompletedProcess(command, 0, "Package: git-lfs\nVersion: 3.6.1\nDescription: Git extension for versioning large files\n", "")
        raise AssertionError(command)

    monkeypatch.setattr(debian_packages.subprocess, "run", run)
    results = debian_packages.search_debian_packages("git")
    assert results == (
        debian_packages.DebianPackage("git", "1:2.47.3-0+deb13u1", "fast, scalable, distributed revision control system"),
        debian_packages.DebianPackage("git-lfs", "3.6.1", "Git extension for versioning large files"),
    )


def test_search_debian_packages_skips_empty_query(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("apt-cache must not be called")
    monkeypatch.setattr(debian_packages.subprocess, "run", unexpected)
    assert debian_packages.search_debian_packages("  ") == ()


def test_available_debian_packages_checks_requested_names(monkeypatch):
    monkeypatch.setattr(
        debian_packages,
        "_package_details",
        lambda name: debian_packages.DebianPackage(name, "1.0", "") if name == "jq" else None,
    )
    assert debian_packages.available_debian_packages(("jq", "missing")) == frozenset({"jq"})


def test_apt_cache_failures_are_reported(monkeypatch):
    def fail(*args, **kwargs):
        raise FileNotFoundError("apt-cache")
    monkeypatch.setattr(debian_packages.subprocess, "run", fail)
    with pytest.raises(DebianPackageSearchError, match="apt-cache"):
        debian_packages.search_debian_packages("git")
