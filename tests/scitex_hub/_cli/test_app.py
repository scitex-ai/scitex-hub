#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ``scitex-hub app *`` CLI verbs.

These tests cover the §2 universal-flag conformance added to the ``app``
command group: ``--dry-run`` for mutating verbs, ``--yes`` to skip
confirmation, ``--json`` for read verbs, and the §4 ``Example:`` help
block.

Real Click ``CliRunner`` is used; no unittest.mock. Where a verb would
reach into the broader ``scitex_hub.appmaker`` package, the test stays
in ``--dry-run`` mode so no side effects are triggered.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from scitex_hub._cli.app import app

# --------------------------------------------------------------------- #
# Mutating verbs — --dry-run + --yes                                   #
# --------------------------------------------------------------------- #

MUTATING_VERBS = [
    # (argv, expect substring in dry-run output)
    (["init", ".", "--dry-run", "--yes"], "would scaffold app"),
    (["install-dev", ".", "--dry-run", "--yes"], "would print dev-server"),
    (
        ["install-deps", ".", "--type", "python", "--dry-run", "--yes"],
        "would install python dependencies",
    ),
    (["build-container", ".", "--dry-run", "--yes"], "would build Apptainer container"),
    (
        ["prefs", "delete", "demo_app", "--dry-run", "--yes"],
        "would delete all preferences",
    ),
]


@pytest.mark.parametrize("argv,expect", MUTATING_VERBS)
def test_mutating_verb_dry_run_prints_plan_and_does_nothing(tmp_path, argv, expect):
    """--dry-run must print the planned action and return cleanly."""
    runner = CliRunner()
    # install-deps wants a manifest.json before the --dry-run guard fires
    if argv[0] == "install-deps":
        (tmp_path / "manifest.json").write_text("{}")
        argv = [argv[0], str(tmp_path), *argv[2:]]
    elif argv[0] in {"init", "install-dev", "build-container"}:
        argv = [argv[0], str(tmp_path), *argv[2:]]
    result = runner.invoke(app, argv)
    assert result.exit_code == 0, result.output
    assert "[dry-run]" in result.output
    assert expect in result.output


@pytest.mark.parametrize("argv,_expect", MUTATING_VERBS)
def test_mutating_verb_yes_short_form_accepted(tmp_path, argv, _expect):
    """The short ``-y`` form is accepted (§2 short/long pairing)."""
    runner = CliRunner()
    # Build the -y variant. Keep --dry-run so we never touch anything real.
    short = [a if a != "--yes" else "-y" for a in argv]
    if short[0] == "install-deps":
        (tmp_path / "manifest.json").write_text("{}")
        short = [short[0], str(tmp_path), *short[2:]]
    elif short[0] in {"init", "install-dev", "build-container"}:
        short = [short[0], str(tmp_path), *short[2:]]
    result = runner.invoke(app, short)
    assert result.exit_code == 0, result.output


# --------------------------------------------------------------------- #
# Read verbs — --json                                                   #
# --------------------------------------------------------------------- #


def test_show_current_json_emits_valid_json(monkeypatch):
    """``app show-current --json`` must round-trip through json.loads."""
    monkeypatch.delenv("SCITEX_CURRENT_APP", raising=False)
    runner = CliRunner()
    result = runner.invoke(app, ["show-current", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "current" in payload


def test_prefs_list_json_emits_valid_json(tmp_path, monkeypatch):
    """``app prefs list --json`` must emit a JSON object, even when empty."""
    # Pin prefs file under tmp so the test never touches a real user config.
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["prefs", "list", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, dict)


def test_prefs_get_json_emits_valid_json(tmp_path, monkeypatch):
    """``app prefs get <name> --json`` must emit a JSON object."""
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["prefs", "get", "writer", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, dict)


# --------------------------------------------------------------------- #
# §4 — every verb's --help must contain a concrete Example:             #
# --------------------------------------------------------------------- #

ALL_LEAF_VERBS = [
    ["init", "--help"],
    ["install-dev", "--help"],
    ["validate", "--help"],
    ["submit", "--help"],
    ["list", "--help"],
    ["show-current", "--help"],
    ["switch", "--help"],
    ["show-info", "--help"],
    ["prefs", "get", "--help"],
    ["prefs", "set", "--help"],
    ["prefs", "delete", "--help"],
    ["prefs", "list", "--help"],
    ["check-deps", "--help"],
    ["install-deps", "--help"],
    ["build-container", "--help"],
]


@pytest.mark.parametrize("argv", ALL_LEAF_VERBS, ids=lambda v: " ".join(v[:-1]))
def test_verb_help_includes_example(argv):
    """§4 — every leaf verb's --help must contain an ``Example:`` block."""
    runner = CliRunner()
    result = runner.invoke(app, argv)
    assert result.exit_code == 0, result.output
    # Auditor regex: ``^\s*examples?:\s*$`` (case-insensitive).
    lower = result.output.lower()
    assert "example:" in lower or "examples:" in lower, result.output


# EOF
