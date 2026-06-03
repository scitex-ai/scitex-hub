#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ``scitex-hub docker *`` CLI verbs.

Covers §2 universal flags (``--dry-run``, ``-y/--yes``, ``--json``) and the
§4 ``Example:`` block. Uses Click's real ``CliRunner`` against the actual
``docker`` group; the ``DockerManager`` is bypassed for all mutating verbs by
running them in ``--dry-run`` mode (which short-circuits before the manager
is invoked). No unittest.mock.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from scitex_hub._cli.docker import docker

MUTATING_VERBS = [
    (["build", "--dry-run", "--yes"], "would build Docker containers"),
    (["up", "--dry-run", "--yes"], "would start Docker containers"),
    (["down", "--dry-run", "--yes"], "would stop Docker containers"),
    (["restart", "--dry-run", "--yes"], "would restart Docker containers"),
]


@pytest.mark.parametrize("argv,expect", MUTATING_VERBS)
def test_docker_verb_dry_run_prints_plan_and_does_nothing(argv, expect):
    runner = CliRunner()
    result = runner.invoke(docker, argv)
    assert result.exit_code == 0, result.output
    assert "[dry-run]" in result.output
    assert expect in result.output


@pytest.mark.parametrize("argv,_expect", MUTATING_VERBS)
def test_docker_verb_yes_short_form_accepted(argv, _expect):
    runner = CliRunner()
    short = [a if a != "--yes" else "-y" for a in argv]
    result = runner.invoke(docker, short)
    assert result.exit_code == 0, result.output


def test_docker_ps_json_emits_valid_json():
    runner = CliRunner()
    result = runner.invoke(docker, ["ps", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "env" in payload


ALL_LEAF_VERBS = [
    ["build", "--help"],
    ["up", "--help"],
    ["down", "--help"],
    ["restart", "--help"],
    ["ps", "--help"],
]


@pytest.mark.parametrize("argv", ALL_LEAF_VERBS, ids=lambda v: v[0])
def test_docker_verb_help_includes_example(argv):
    runner = CliRunner()
    result = runner.invoke(docker, argv)
    assert result.exit_code == 0, result.output
    lower = result.output.lower()
    assert "example:" in lower or "examples:" in lower, result.output


# EOF
