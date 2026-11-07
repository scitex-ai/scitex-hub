"""Exercise real Git/tag metadata and the release dependency/publishing boundary."""

import importlib.util
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "release_version_guard", ROOT / ".github/ci/check_release_version.py"
)
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


@pytest.fixture
def repository(tmp_path):
    """Own a clean repository; no inherited signing/hooks/branch assumptions."""
    root = tmp_path / "repo"
    root.mkdir()

    def git(*args):
        return subprocess.check_output(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "user.name=Release Test",
                "-c",
                "user.email=release@example.invalid",
                *args,
            ],
            cwd=root,
            text=True,
        )

    git("init", "--initial-branch=main")
    (root / "pyproject.toml").write_text('[project]\nversion = "0.22.0a0"\n')
    git("add", "pyproject.toml")
    git("commit", "-m", "Owned release fixture")
    git("tag", "v0.22.0a0")
    return root, git


def test_real_alpha_tag_matches_package_and_checkout(repository):
    root, _ = repository
    assert GUARD.check_release(root, "v0.22.0a0") is True


@pytest.mark.parametrize("tag", ["v0.22.0-alpha", "v0.21.0", "refs/heads/main"])
def test_mismatched_or_noncanonical_tag_is_refused(repository, tag):
    root, _ = repository
    with pytest.raises(ValueError, match="tag does not match"):
        GUARD.check_release(root, tag)


def test_tag_on_another_commit_is_refused(repository):
    root, git = repository
    (root / "note.txt").write_text("new commit")
    git("add", "note.txt")
    git("commit", "-m", "Different checkout")
    with pytest.raises(ValueError, match="Checkout does not match"):
        GUARD.check_release(root, "v0.22.0a0")


def test_stable_release_is_not_marked_prerelease(repository):
    root, git = repository
    (root / "pyproject.toml").write_text('[project]\nversion = "0.22.0"\n')
    git("add", "pyproject.toml")
    git("commit", "-m", "Stable release")
    git("tag", "v0.22.0")
    assert GUARD.check_release(root, "v0.22.0") is False


def test_publisher_requires_full_dependencies_and_ordinary_review():
    source = (
        ROOT / ".github/workflows/pypi-publish-and-github-release-on-tag.yml"
    ).read_text()
    workflow = yaml.safe_load(source)
    jobs = workflow["jobs"]
    matrix_file = "pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml"
    assert jobs["test"]["uses"] == f"./.github/workflows/{matrix_file}"
    assert jobs["test"]["with"]["release_tag"] == (
        "${{ github.event_name == 'push' && github.ref_name || inputs.version }}"
    )
    matrix = yaml.safe_load((ROOT / ".github/workflows" / matrix_file).read_text())
    steps = matrix["jobs"]["test"]["steps"]
    install = next(
        s for s in steps if s.get("name", "").startswith("Install dependencies")
    )
    assert '-e ".[all,dev]"' in install["run"]
    assert "||" not in install["run"]
    tag_guard = next(
        s for s in steps if s.get("name") == "Verify release tag and checkout"
    )
    assert tag_guard["env"]["RELEASE_TAG"] == "${{ inputs.release_tag }}"
    assert 'check_release_version.py --tag "$RELEASE_TAG"' in tag_guard["run"]
    guard = next(s for s in jobs["build"]["steps"] if s.get("id") == "release_metadata")
    assert 'check_release_version.py --tag "$RELEASE_TAG"' in guard["run"]
    assert all("self-hosted" in j["runs-on"] for j in jobs.values() if "runs-on" in j)
    release = next(
        s for s in jobs["release"]["steps"] if s.get("name") == "Create GitHub Release"
    )
    assert "--prerelease" in release["run"]
    assert (
        release["env"]["RELEASE_PRERELEASE"] == "${{ needs.build.outputs.prerelease }}"
    )
    assert "--admin" not in source
    assert "gh pr merge" not in source


def test_audit_corpus_pin_satisfies_declared_dev_requirements():
    """The native audit must not downgrade below the package it just installed."""
    import shlex
    import tomllib

    from packaging.requirements import Requirement

    workflow = yaml.safe_load(
        (
            ROOT / ".github/workflows/scitex-hub-quality-audit-on-ubuntu-latest.yml"
        ).read_text()
    )
    install = next(
        step
        for step in workflow["jobs"]["audit"]["steps"]
        if step.get("name") == "Install package + audit tooling"
    )
    pins = [
        Requirement(token)
        for line in install["run"].splitlines()
        for token in shlex.split(line, comments=True)
        if token.startswith("scitex-dev==")
    ]
    assert len(pins) == 1
    pin = next(iter(pins[0].specifier)).version
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    declarations = project["dependencies"] + [
        req for group in project["optional-dependencies"].values() for req in group
    ]
    requirements = [Requirement(raw) for raw in declarations]
    assert all(
        req.specifier.contains(pin) for req in requirements if req.name == "scitex-dev"
    )
