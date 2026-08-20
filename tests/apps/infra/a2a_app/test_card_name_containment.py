#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`load_card` must not let a URL-supplied agent name reach outside the agents dir.

WHY THIS FILE IS SEPARATE FROM test_card_schema.py
--------------------------------------------------
The neighbouring schema tests call
``pytest.skip("no agents available — SCITEX_OROCHI_AGENTS_DIR not mounted")``
whenever the real fleet directory is absent, which is the normal state in CI.
A security test that skips exactly where it is not being watched is not a
test, so these build their OWN agents directory in a tmp path and point
``SCITEX_OROCHI_AGENTS_DIR`` at it. They run everywhere, every time.

``/v1/agents/<name>`` is a PUBLIC route, so ``name`` is attacker-controlled.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from apps.infra.a2a_app import _card


@pytest.fixture()
def agents_dir(tmp_path, monkeypatch):
    """A minimal but REAL agents dir, plus a secret outside it to aim at."""
    root = tmp_path / "agents"
    good = root / "scitex-hub"
    good.mkdir(parents=True)
    (good / "scitex-hub.yaml").write_text("name: scitex-hub\ndescription: ok\n")

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "outside.yaml").write_text("name: pwned\n")

    monkeypatch.setenv("SCITEX_OROCHI_AGENTS_DIR", str(root))
    return root


def test_positive_control_a_real_agent_still_loads(agents_dir):
    """Without this, every rejection below would pass on a broken loader."""
    card = _card.load_card("scitex-hub")
    assert card is not None
    assert card["name"] == "scitex-hub"


@pytest.mark.parametrize(
    "name",
    [
        "..",
        ".",
        "../outside",
        "../../etc",
        "scitex-hub/../../outside",
        "/etc/passwd",
        "sub/nested",
        "",
        "-leading-dash-is-not-a-name",
        "with space",
        "nul\x00byte",
        "x" * 200,
    ],
)
def test_names_that_are_not_a_single_segment_are_rejected(agents_dir, name):
    assert _card.load_card(name) is None


def test_cannot_read_a_yaml_outside_the_agents_dir(agents_dir, tmp_path):
    """The concrete attack: reach ../outside/outside.yaml and get it projected."""
    assert (tmp_path / "outside" / "outside.yaml").exists()  # target really is there
    assert _card.load_card("../outside") is None


def test_symlinked_agent_pointing_outside_is_rejected(agents_dir, tmp_path):
    link = agents_dir / "sneaky"
    try:
        link.symlink_to(tmp_path / "outside")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    # The NAME is a valid single segment, so only real containment catches this.
    assert _card.load_card("sneaky") is None


def test_unknown_but_well_formed_name_is_a_plain_miss(agents_dir):
    """A legitimate 404 must stay a 404 — the guard must not break normal use."""
    assert _card.load_card("no-such-agent") is None


def test_agents_dir_env_is_honoured(agents_dir):
    assert _card._agents_dir() == Path(os.environ["SCITEX_OROCHI_AGENTS_DIR"])
