#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the `app prefs update` §2 flag conformance (mutating verb)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from scitex_hub._cli._app._prefs import app_prefs


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_update_dry_run_exits_zero(runner):
    # Arrange
    args = ["update", "writer", "theme=dark", "--dry-run"]
    # Act
    result = runner.invoke(app_prefs, args)
    # Assert
    assert result.exit_code == 0


def test_update_dry_run_does_not_claim_saved(runner):
    # Arrange
    args = ["update", "writer", "theme=dark", "--dry-run"]
    # Act
    result = runner.invoke(app_prefs, args)
    # Assert
    assert "Saved" not in result.output


def test_update_without_yes_refuses_exit_2(runner):
    # Arrange: mutating verb without --yes must refuse (never prompt)
    args = ["update", "writer", "theme=dark"]
    # Act
    result = runner.invoke(app_prefs, args)
    # Assert
    assert result.exit_code == 2


def test_update_rejects_malformed_pair(runner):
    # Arrange: missing '=' separator
    args = ["update", "writer", "theme", "--dry-run"]
    # Act
    result = runner.invoke(app_prefs, args)
    # Assert
    assert result.exit_code == 1


def test_update_help_advertises_dry_run(runner):
    # Arrange
    args = ["update", "--help"]
    # Act
    result = runner.invoke(app_prefs, args)
    # Assert
    assert "--dry-run" in result.output


# EOF
