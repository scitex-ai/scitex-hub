#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Top-level ``scitex-hub`` CLI conformance tests (§2 universal flags).

The CLI noun-verb convention (§2) requires the root command to expose:
  * ``-V`` and ``--version`` (both short and long forms)
  * ``-h`` and ``--help`` (both forms)
  * ``--help-recursive``
  * ``--json`` (universal machine-readable output)

These tests use Click's ``CliRunner`` against the real ``main`` group; no
mocks are involved.
"""

from __future__ import annotations

from click.testing import CliRunner

from scitex_hub._cli.main import main


def test_root_version_long_form_prints_version():
    """``scitex-hub --version`` must succeed and print a version line."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0, result.output
    assert "scitex-hub" in result.output


def test_root_version_short_form_prints_version():
    """``scitex-hub -V`` must succeed and print a version line."""
    runner = CliRunner()
    result = runner.invoke(main, ["-V"])
    assert result.exit_code == 0, result.output
    assert "scitex-hub" in result.output


def test_root_help_includes_recursive_and_json_flags():
    """The root --help must advertise --help-recursive and --json."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    assert "--help-recursive" in result.output
    assert "--json" in result.output


def test_root_help_includes_example_block():
    """§4 — root --help must contain an Example: block."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    lower = result.output.lower()
    assert "example:" in lower or "examples:" in lower


def test_root_json_flag_is_accepted():
    """``scitex-hub --json --help`` parses cleanly (universal flag presence)."""
    runner = CliRunner()
    result = runner.invoke(main, ["--json", "--help"])
    assert result.exit_code == 0, result.output


# EOF
