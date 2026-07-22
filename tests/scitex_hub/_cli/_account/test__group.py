#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the `account` CLI group wiring (scitex_hub._cli._account._group)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from scitex_hub._cli._account._group import account


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_account_help_exits_zero(runner):
    # Arrange
    args = ["--help"]
    # Act
    result = runner.invoke(account, args)
    # Assert
    assert result.exit_code == 0


def test_account_nests_token_group(runner):
    # Arrange
    args = ["--help"]
    # Act
    result = runner.invoke(account, args)
    # Assert
    assert "token" in result.output


def test_token_group_lists_revoke(runner):
    # Arrange
    args = ["token", "--help"]
    # Act
    result = runner.invoke(account, args)
    # Assert
    assert "revoke" in result.output


# EOF
