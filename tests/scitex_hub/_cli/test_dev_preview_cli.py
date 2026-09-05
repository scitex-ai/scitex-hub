#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/_cli/test_dev_preview_cli.py

"""``scitex-hub dev-preview sync`` — the click surface the supervisor invokes.

The periodic job runs exactly ``scitex-hub dev-preview sync --clone <clone>``
with stdout discarded, so the CLI contract is: JSON on stdout, the outcome's
exit code, a usage error (2) when ``--clone`` is missing, and a place in the
root help's ``Service`` category next to ``docker`` / ``mcp``. Each test
drives the real ``main`` group through ``CliRunner`` against a real bare
origin + clone in ``tmp_path`` (``--dry-run`` fetches, so the clone needs a
reachable remote); no mocks.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Iterator

import pytest
from click.testing import CliRunner

from scitex_hub._cli._click_compat import HAS_CLI_HELPERS
from scitex_hub._cli.main import main

requires_cli_helpers = pytest.mark.skipif(
    not HAS_CLI_HELPERS,
    reason="released scitex-dev lacks help_spec (categorized help skipped)",
)


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return completed.stdout.strip()


@pytest.fixture(autouse=True)
def isolated_git_config(tmp_path: Path) -> Iterator[None]:
    """Empty global git config so host signing/hook settings cannot leak in (real env, restored)."""
    empty = tmp_path / "gitconfig.empty"
    empty.write_text("", encoding="utf-8")
    previous = {
        k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")
    }
    os.environ["GIT_CONFIG_GLOBAL"] = str(empty)
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    yield
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """A clone on ``develop`` whose ``origin`` is a bare repo in ``tmp_path``."""
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "--quiet", "-b", "develop")
    _git(seed, "config", "user.email", "dev-preview-test@example.com")
    _git(seed, "config", "user.name", "dev-preview test")
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "--quiet", "-m", "seed")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "clone", "--quiet", "--bare", str(seed), str(origin))
    target = tmp_path / "clone"
    _git(tmp_path, "clone", "--quiet", "--branch", "develop", str(origin), str(target))
    return target


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _help_section(output: str, heading: str) -> list[str]:
    """The command names listed under ``heading`` in a categorized root help."""
    names: list[str] = []
    collecting = False
    for line in output.splitlines():
        if line.strip() == heading:
            collecting = True
            continue
        if collecting:
            if not line.strip():
                break
            if line.startswith("  ") and not line.startswith("    "):
                names.append(line.split()[0])
    return names


def test_sync_dry_run_exits_zero_with_a_planned_status(
    runner: CliRunner, clone: Path, tmp_path: Path
):
    """A dry run against a clean clone plans (first run: baseline) and moves nothing."""
    # Arrange
    argv = [
        "dev-preview",
        "sync",
        "--dry-run",
        "--clone",
        str(clone),
        "--state-dir",
        str(tmp_path / "state"),
    ]
    # Act
    result = runner.invoke(main, argv)
    payload = json.loads(result.stdout)
    # Assert
    assert (result.exit_code, payload["status"] in {"dry_run", "noop"}) == (
        0,
        True,
    ), result.output


def test_sync_no_cards_refusal_exits_two_and_only_logs_the_card(
    runner: CliRunner, clone: Path, tmp_path: Path
):
    """``--no-cards`` keeps a manual run's refusal off the operator's real board.

    The shell this suite may run in points SCITEX_CARDS_DB at the fleet store,
    so this is also the only CLI path to ``refused`` a test may take.
    """
    # Arrange
    state_dir = tmp_path / "state"
    common = ["--no-cards", "--clone", str(clone), "--state-dir", str(state_dir)]
    runner.invoke(main, ["dev-preview", "sync", *common])  # baseline tick
    (clone / "README.md").write_text("operator edit in progress\n", encoding="utf-8")
    # Act
    result = runner.invoke(main, ["dev-preview", "sync", *common])
    payload = json.loads(result.stdout)
    log = (state_dir / "sync.log").read_text(encoding="utf-8")
    # Assert
    assert (result.exit_code, payload["status"], "skipped (--no-cards)" in log) == (
        2,
        "refused",
        True,
    ), result.output


def test_sync_without_clone_is_a_usage_error(runner: CliRunner):
    """The clone is the one thing the verb cannot guess; missing it is exit 2."""
    # Arrange
    argv = ["dev-preview", "sync"]
    env = {"SCITEX_HUB_DEV_PREVIEW_CLONE": None}
    # Act
    result = runner.invoke(main, argv, env=env)
    # Assert
    assert (result.exit_code, "Missing option '--clone'" in result.output) == (
        2,
        True,
    ), result.output


def test_root_help_lists_dev_preview(runner: CliRunner):
    """The verb is discoverable from the root help on every scitex-dev generation."""
    # Arrange
    argv = ["--help"]
    # Act
    result = runner.invoke(main, argv)
    # Assert
    assert "dev-preview" in result.output


@requires_cli_helpers
def test_root_help_places_dev_preview_under_service(runner: CliRunner):
    """Doctrine §4a: infrastructure verbs live in Service beside docker / mcp / sdk."""
    # Arrange
    argv = ["--help"]
    # Act
    result = runner.invoke(main, argv)
    # Assert
    assert _help_section(result.output, "Service:") == [
        "docker",
        "mcp",
        "sdk",
        "dev-preview",
    ]


def test_sync_help_exits_zero_with_the_exit_code_legend(runner: CliRunner):
    """The leaf documents its exit codes — the only thing a supervisor log shows."""
    # Arrange
    argv = ["dev-preview", "sync", "--help"]
    # Act
    result = runner.invoke(main, argv)
    # Assert
    assert (result.exit_code, "3 held" in result.output) == (0, True), result.output


# EOF
