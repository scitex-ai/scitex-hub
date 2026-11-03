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
    install = next(
        s
        for s in jobs["test"]["steps"]
        if s.get("name") == "Install full declared test dependencies"
    )
    assert '-e ".[all,dev]"' in install["run"]
    assert "||" not in install["run"]
    for job in ("test", "build"):
        steps = jobs[job]["steps"]
        guard = next(s for s in steps if s.get("id") == "release_metadata")
        assert 'check_release_version.py --tag "$RELEASE_TAG"' in guard["run"]
    release = next(
        s for s in jobs["release"]["steps"] if s.get("name") == "Create GitHub Release"
    )
    assert "--prerelease" in release["run"]
    assert (
        release["env"]["RELEASE_PRERELEASE"] == "${{ needs.build.outputs.prerelease }}"
    )
    assert "--admin" not in source
    assert "gh pr merge" not in source
