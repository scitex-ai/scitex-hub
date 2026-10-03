"""Offline real-Git controls for the immutable frontend acquisition seam."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "hub_frontend_sources", ROOT / "scripts/apps/prepare_frontend_sources.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def git(root, *arguments):
    return subprocess.run(
        ["git", "-C", str(root), *arguments], check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def commit(root):
    git(root, "add", ".")
    git(root, "-c", "user.name=Owned fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--quiet", "-m", "Owned offline fixture")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def source(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    git(origin, "init", "--quiet")
    package = origin / "package.json"
    package.write_text(json.dumps({"name": "owned-fixture", "version": "1.0.0"}))
    (origin / "src").mkdir()
    (origin / "src/value.ts").write_text("export const value = 42;\n")
    (origin / "docs").mkdir()
    (origin / "docs/value.ts").symlink_to("../src/value.ts")
    revision = commit(origin)
    return MODULE.Source(
        "checkout", origin.as_uri(), revision, "package.json",
        hashlib.sha256(package.read_bytes()).hexdigest(),
    )


def test_acquires_exact_local_git_bytes_and_literal_documentation_link(tmp_path, source):
    # Arrange
    parent = tmp_path / "sources"
    parent.mkdir()

    # Act
    receipt = MODULE.acquire_source(parent, source)
    root = parent / source.name

    # Assert
    assert (receipt, git(root, "rev-parse", "HEAD"),
            (root / "src/value.ts").read_text(), os.readlink(root / "docs/value.ts")) == (
        {"name": source.name, "commit": source.commit, "tracked_entries": 3},
        source.commit, "export const value = 42;\n", "../src/value.ts",
    )


def test_reuses_verified_checkout_without_an_available_source_remote(tmp_path, source):
    # Arrange
    MODULE.acquire_source(tmp_path, source)
    unavailable = MODULE.Source(
        source.name, (tmp_path / "absent-origin").as_uri(), source.commit,
        source.package, source.package_sha256,
    )
    before = (tmp_path / source.name / "src/value.ts").stat().st_mtime_ns

    # Act
    receipt = MODULE.acquire_source(tmp_path, unavailable)

    # Assert
    assert (receipt["commit"], (tmp_path / source.name / "src/value.ts").stat().st_mtime_ns) == (
        source.commit, before,
    )


def test_refuses_a_different_commit_without_resetting_it(tmp_path, source):
    # Arrange
    MODULE.acquire_source(tmp_path, source)
    root = tmp_path / source.name
    (root / "src/value.ts").write_text("export const value = 99;\n")
    changed = commit(root)

    # Act
    with pytest.raises(ValueError, match="different commit"):
        MODULE.acquire_source(tmp_path, source)

    # Assert
    assert git(root, "rev-parse", "HEAD") == changed


@pytest.mark.parametrize("hidden", [False, True], ids=["ordinary", "assume-unchanged"])
def test_refuses_dirty_source_even_when_git_status_hides_it(tmp_path, source, hidden):
    # Arrange
    MODULE.acquire_source(tmp_path, source)
    root = tmp_path / source.name
    commands = {False: ["update-index", "--no-assume-unchanged", "src/value.ts"],
                True: ["update-index", "--assume-unchanged", "src/value.ts"]}
    git(root, *commands[hidden])
    (root / "src/value.ts").write_text("private edit must survive\n")

    # Act
    with pytest.raises(ValueError):
        MODULE.acquire_source(tmp_path, source)

    # Assert
    assert (root / "src/value.ts").read_text() == "private edit must survive\n"


def test_refuses_root_symlink_without_touching_its_destination(tmp_path, source):
    # Arrange
    destination = tmp_path / "destination"
    destination.mkdir()
    (tmp_path / source.name).symlink_to(destination, target_is_directory=True)

    # Act
    with pytest.raises(ValueError, match="regular directory"):
        MODULE.acquire_source(tmp_path, source)

    # Assert
    assert list(destination.iterdir()) == []


def test_refuses_regular_file_ancestor_symlink(tmp_path, source):
    # Arrange
    MODULE.acquire_source(tmp_path, source)
    root = tmp_path / source.name
    (root / "src").rename(root / "retained-src")
    (root / "src").symlink_to("retained-src", target_is_directory=True)

    # Act
    with pytest.raises(ValueError):
        MODULE.acquire_source(tmp_path, source)

    # Assert
    assert (root / "src").is_symlink()


def test_failed_acquisition_never_falls_back_to_existing_or_generated_packages(tmp_path, source):
    # Arrange
    missing = MODULE.Source(
        source.name, (tmp_path / "absent-origin").as_uri(), source.commit,
        source.package, source.package_sha256,
    )

    # Act
    with pytest.raises(subprocess.CalledProcessError):
        MODULE.acquire_source(tmp_path, missing)

    # Assert
    assert not (tmp_path / source.name / source.package).exists()


def test_refuses_changed_hub_declarations_before_any_source_acquisition(tmp_path):
    # Arrange
    project = tmp_path / "Hub"
    project.mkdir()
    (project / "package.json").write_text(json.dumps({"dependencies": {}}))

    # Act
    with pytest.raises(ValueError, match="declarations changed"):
        MODULE.prepare(project)

    # Assert
    assert sorted(path.name for path in tmp_path.iterdir()) == ["Hub"]


def test_ci_callers_retain_test_commands_and_prepare_before_normal_install():
    # Arrange
    workflow = (ROOT / ".github/workflows/tests.yml").read_text()
    typescript = workflow.split("  typescript-check:", 1)[1].split("  vitest:", 1)[0]
    vitest = workflow.split("  vitest:", 1)[1].split("  terminal-tests:", 1)[0]

    # Act
    observation = [
        "python3 scripts/apps/prepare_frontend_sources.py" in block
        and block.index("prepare_frontend_sources.py") < block.index("npm run frontend:install")
        for block in (typescript, vitest)
    ]

    # Assert
    assert (observation, "run: npm run build" in typescript,
            "run: npm run test:run" in vitest, "install_apps.sh --clone" in typescript) == (
        [True, True], True, True, True,
    )
