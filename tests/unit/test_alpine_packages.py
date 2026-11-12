"""Unit tests for external Alpine package discovery."""

from devbox_manager import alpine_packages
from devbox_manager.alpine_packages import AlpinePackage, AlpinePackageSearchError


def test_parse_index_extracts_package_metadata():
    content = (
        b"P:git\nV:2.50.1-r0\nA:x86_64\nT:Distributed version control system\n"
        b"\nP:git-lfs\nV:3.6.1-r0\nA:x86_64\nT:Git extension for large files\n"
    )

    import io
    import tarfile

    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo("APKINDEX")
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))

    packages = alpine_packages._parse_index(
        archive_buffer.getvalue(), "main", "x86_64", "3.22"
    )

    assert packages == [
        AlpinePackage(
            name="git",
            version="2.50.1-r0",
            description="Distributed version control system",
            repository="main",
            architecture="x86_64",
            alpine_version="3.22",
        ),
        AlpinePackage(
            name="git-lfs",
            version="3.6.1-r0",
            description="Git extension for large files",
            repository="main",
            architecture="x86_64",
            alpine_version="3.22",
        ),
    ]


def test_search_queries_main_and_community_and_matches_descriptions(monkeypatch):
    repositories = {
        "main": [
            AlpinePackage("git", "2.50-r0", "Distributed version control", "main", "x86_64", "3.22"),
            AlpinePackage("curl", "8.10-r0", "Transfer data", "main", "x86_64", "3.22"),
        ],
        "community": [
            AlpinePackage("git-lfs", "3.6-r0", "Git extension for large files", "community", "x86_64", "3.22"),
        ],
    }
    calls = []

    monkeypatch.setattr(alpine_packages, "_current_alpine_version", lambda: "3.22")
    monkeypatch.setattr(alpine_packages, "_current_architecture", lambda: "x86_64")

    def fetch(version, architecture, repository):
        calls.append(repository)
        return repositories[repository]

    monkeypatch.setattr(alpine_packages, "_fetch_repository_index", fetch)

    results = alpine_packages.search_alpine_packages("GIT")

    assert calls == ["main", "community"]
    assert [package.name for package in results] == ["git", "git-lfs"]


def test_search_returns_empty_for_blank_query(monkeypatch):
    def unexpected_call():
        raise AssertionError("Blank searches should not access the system or network.")

    monkeypatch.setattr(alpine_packages, "_current_alpine_version", unexpected_call)

    assert alpine_packages.search_alpine_packages("  ") == ()


def test_current_architecture_maps_common_platform_names(monkeypatch):
    monkeypatch.setattr(alpine_packages.platform, "machine", lambda: "aarch64")

    assert alpine_packages._current_architecture() == "aarch64"


def test_current_architecture_rejects_unknown_platform(monkeypatch):
    monkeypatch.setattr(alpine_packages.platform, "machine", lambda: "mips64")

    try:
        alpine_packages._current_architecture()
    except AlpinePackageSearchError as error:
        assert "Unsupported Alpine package architecture" in str(error)
    else:
        raise AssertionError("Unsupported architectures must be rejected.")


def test_parse_index_rejects_invalid_archive():
    try:
        alpine_packages._parse_index(b"not an archive", "main", "x86_64", "3.22")
    except AlpinePackageSearchError as error:
        assert "package index is invalid" in str(error)
    else:
        raise AssertionError("Invalid archives must be rejected.")



def test_available_alpine_packages_checks_both_repositories_once(monkeypatch):
    repositories = {
        "main": [
            AlpinePackage("nodejs", "22.23-r0", "JavaScript runtime", "main", "x86_64", "3.22"),
        ],
        "community": [
            AlpinePackage("opentofu", "1.9-r0", "Infrastructure as code", "community", "x86_64", "3.22"),
        ],
    }
    calls = []

    monkeypatch.setattr(alpine_packages, "_current_alpine_version", lambda: "3.22")
    monkeypatch.setattr(alpine_packages, "_current_architecture", lambda: "x86_64")

    def fetch(version, architecture, repository):
        calls.append(repository)
        return repositories[repository]

    monkeypatch.setattr(alpine_packages, "_fetch_repository_index", fetch)

    result = alpine_packages.available_alpine_packages(
        ("nodejs", "opentofu", "venv", "potato")
    )

    assert result == frozenset({"nodejs", "opentofu"})
    assert calls == ["main", "community"]


def test_available_alpine_packages_skips_repository_lookup_for_empty_input(monkeypatch):
    def unexpected_call(*args):
        raise AssertionError("Empty package lists should not query repositories.")

    monkeypatch.setattr(alpine_packages, "_current_alpine_version", unexpected_call)

    assert alpine_packages.available_alpine_packages(()) == frozenset()
